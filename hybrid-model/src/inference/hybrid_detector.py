"""
Hybrid detector combining YOLO and LSTM for real-time milking detection.
"""

import numpy as np
import torch
from collections import deque
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ModelConfig
from detection.yolo_detector import YOLOFeatureExtractor, FrameFeatures
from temporal.lstm_model import MilkingActionLSTM


@dataclass
class MilkingDetection:
    """Result of milking action detection."""
    task_id: str
    task_name: str
    confidence: float
    timestamp: float
    person_detected: bool
    objects_detected: List[str]
    attention_weights: Optional[np.ndarray] = None


class HybridDetector:
    """
    Real-time milking detection using YOLO + LSTM.
    
    This detector:
    1. Uses YOLO to detect objects in each frame
    2. Accumulates features over a sequence of frames
    3. Uses LSTM to classify the action being performed
    4. Maps the action to a milking task
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the hybrid detector.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Initialize YOLO feature extractor
        self.yolo = YOLOFeatureExtractor(config.yolo)
        
        # Initialize LSTM model
        self.lstm = MilkingActionLSTM(
            input_size=config.lstm.input_size,
            hidden_size=config.lstm.hidden_size,
            num_layers=config.lstm.num_layers,
            num_classes=config.lstm.num_classes,
            dropout=config.lstm.dropout,
            bidirectional=config.lstm.bidirectional
        ).to(self.device)
        
        # Load trained weights if available
        self._load_weights()
        
        # Frame buffer for sequence
        self.frame_buffer = deque(maxlen=config.lstm.sequence_length)
        self.feature_buffer = deque(maxlen=config.lstm.sequence_length)
        
        # Task labels
        self.task_labels = config.lstm.task_labels
        self.task_names = [
            "Pre-cleaning",
            "Stripping",
            "Machine attachment",
            "Milking (active)",
            "Detachment",
            "Post-dip"
        ]
        
        # Performance tracking
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.current_fps = 0.0
    
    def _load_weights(self):
        """Load trained LSTM weights if available."""
        weights_path = Path(self.config.checkpoints_dir) / "best_model.pt"
        
        if weights_path.exists():
            checkpoint = torch.load(weights_path, map_location=self.device)
            self.lstm.load_state_dict(checkpoint['model_state_dict'])
            print(f"Loaded weights from {weights_path}")
        else:
            print(f"No weights found at {weights_path}, using random initialization")
    
    def process_frame(
        self,
        frame: np.ndarray,
        roi: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[MilkingDetection]:
        """
        Process a single frame and return detection if available.
        
        Args:
            frame: BGR image (H, W, 3)
            roi: Optional region of interest (x, y, width, height)
        
        Returns:
            MilkingDetection if sequence is complete, None otherwise
        """
        # Extract features from frame
        frame_features = self.yolo.extract_features(frame)
        
        # Add to buffer
        self.feature_buffer.append(frame_features.feature_vector)
        
        # Update FPS counter
        self._update_fps()
        
        # Check if we have enough frames
        if len(self.feature_buffer) < self.config.lstm.sequence_length:
            return None
        
        # Create sequence tensor
        sequence = np.array(list(self.feature_buffer))
        sequence_tensor = torch.FloatTensor(sequence).unsqueeze(0).to(self.device)
        
        # Run LSTM inference
        with torch.no_grad():
            output, attention_weights = self.lstm(sequence_tensor, return_attention=True)
            probabilities = torch.softmax(output, dim=1)
        
        # Get prediction
        confidence, predicted_idx = torch.max(probabilities, dim=1)
        confidence = confidence.item()
        predicted_idx = predicted_idx.item()
        
        # Apply threshold
        if confidence < self.config.inference.lstm_threshold:
            return None
        
        # Get task info
        task_id = self.task_labels[predicted_idx]
        task_name = self.task_names[predicted_idx]
        
        # Get attention weights for interpretability
        attention = attention_weights.squeeze().cpu().numpy() if attention_weights is not None else None
        
        # Get detected objects
        objects_detected = [det.class_name for det in frame_features.detections]
        
        return MilkingDetection(
            task_id=task_id,
            task_name=task_name,
            confidence=confidence,
            timestamp=time.time(),
            person_detected=frame_features.person_detected,
            objects_detected=objects_detected,
            attention_weights=attention
        )
    
    def _update_fps(self):
        """Update FPS counter."""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter / (current_time - self.fps_timer)
            self.fps_counter = 0
            self.fps_timer = current_time
    
    def get_fps(self) -> float:
        """Get current FPS."""
        return self.current_fps
    
    def reset(self):
        """Reset the detector state."""
        self.frame_buffer.clear()
        self.feature_buffer.clear()
    
    def detect_continuous(
        self,
        source: str,
        show_display: bool = True,
        roi: Optional[Tuple[int, int, int, int]] = None
    ):
        """
        Run continuous detection on video stream.
        
        Args:
            source: Video source (RTSP URL or file path)
            show_display: Whether to show visualization
            roi: Optional region of interest
        """
        import cv2
        
        # Open video source
        cap = cv2.VideoCapture(source)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video source: {source}")
        
        print(f"Starting detection on {source}")
        print(f"Press 'q' to quit")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Process frame
                detection = self.process_frame(frame, roi)
                
                # Visualize
                if show_display:
                    display_frame = self._visualize_frame(frame, detection)
                    cv2.imshow("Milking Detection", display_frame)
                    
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                # Print detection
                if detection:
                    print(f"Detected: {detection.task_name} "
                          f"(confidence: {detection.confidence:.2f}, "
                          f"FPS: {self.current_fps:.1f})")
        
        finally:
            cap.release()
            if show_display:
                cv2.destroyAllWindows()
    
    def _visualize_frame(
        self,
        frame: np.ndarray,
        detection: Optional[MilkingDetection]
    ) -> np.ndarray:
        """
        Add visualization to frame.
        
        Args:
            frame: Original frame
            detection: Current detection
        
        Returns:
            Annotated frame
        """
        import cv2
        
        display_frame = frame.copy()
        
        # Add FPS counter
        cv2.putText(
            display_frame,
            f"FPS: {self.current_fps:.1f}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )
        
        # Add detection info
        if detection:
            # Task name
            cv2.putText(
                display_frame,
                f"Task: {detection.task_name}",
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Confidence
            cv2.putText(
                display_frame,
                f"Confidence: {detection.confidence:.2f}",
                (10, 110),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Person status
            person_status = "Yes" if detection.person_detected else "No"
            cv2.putText(
                display_frame,
                f"Person: {person_status}",
                (10, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2
            )
            
            # Objects detected
            if detection.objects_detected:
                objects_text = ", ".join(detection.objects_detected[:3])
                cv2.putText(
                    display_frame,
                    f"Objects: {objects_text}",
                    (10, 190),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2
                )
        
        return display_frame


def main():
    """Main function for running the hybrid detector."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run hybrid YOLO + LSTM detection")
    parser.add_argument("--source", type=str, required=True,
                        help="Video source (RTSP URL or file path)")
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Path to config file")
    parser.add_argument("--no-display", action="store_true",
                        help="Disable display window")
    
    args = parser.parse_args()
    
    # Load config
    from config import load_config
    config = load_config(args.config)
    
    # Create detector
    detector = HybridDetector(config)
    
    # Run detection
    detector.detect_continuous(
        source=args.source,
        show_display=not args.no_display
    )


if __name__ == "__main__":
    main()
