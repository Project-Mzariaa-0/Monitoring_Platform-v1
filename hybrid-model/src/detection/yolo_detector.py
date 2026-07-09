"""
YOLO-based feature extractor for the hybrid model.
"""

import numpy as np
import torch
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Detection:
    """Single object detection."""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    center: Tuple[int, int]  # center x, center y


@dataclass
class FrameFeatures:
    """Features extracted from a single frame."""
    detections: List[Detection]
    feature_vector: np.ndarray  # 256-dim feature vector
    person_detected: bool
    person_bbox: Optional[Tuple[int, int, int, int]] = None
    person_center: Optional[Tuple[int, int]] = None


class YOLOFeatureExtractor:
    """
    Extract features from frames using YOLO.
    
    This class uses YOLOv8 to detect objects in each frame and
    creates a feature vector for the LSTM temporal model.
    """
    
    def __init__(self, config):
        """
        Initialize the YOLO feature extractor.
        
        Args:
            config: YOLOConfig instance
        """
        from ultralytics import YOLO
        
        self.config = config
        self.model = YOLO(config.model)
        self.device = config.device
        
        # COCO class names (only the ones we care about)
        self.target_classes = {
            0: "person",
            15: "cat",  # Just for testing
            16: "dog",  # Just for testing
        }
        
        # Feature vector size
        self.feature_size = 256
    
    def extract_features(self, frame: np.ndarray) -> FrameFeatures:
        """
        Extract features from a single frame.
        
        Args:
            frame: BGR image (H, W, 3)
        
        Returns:
            FrameFeatures with detections and feature vector
        """
        # Run YOLO inference
        results = self.model(frame, conf=self.config.confidence, verbose=False)
        
        detections = []
        feature_vector = np.zeros(self.feature_size)
        
        for result in results:
            if result.boxes is None:
                continue
            
            for box in result.boxes:
                cls_id = int(box.cls.item())
                confidence = float(box.conf.item())
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                # Convert to our format
                bbox = (
                    int(x1),
                    int(y1),
                    int(x2 - x1),
                    int(y2 - y1)
                )
                center = (
                    int((x1 + x2) / 2),
                    int((y1 + y2) / 2)
                )
                
                class_name = self.model.names.get(cls_id, f"class_{cls_id}")
                
                detection = Detection(
                    class_id=cls_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox=bbox,
                    center=center
                )
                detections.append(detection)
        
        # Create feature vector
        feature_vector = self._create_feature_vector(detections, frame.shape)
        
        # Check for person
        person_detected = False
        person_bbox = None
        person_center = None
        
        for det in detections:
            if det.class_name == "person":
                person_detected = True
                person_bbox = det.bbox
                person_center = det.center
                break
        
        return FrameFeatures(
            detections=detections,
            feature_vector=feature_vector,
            person_detected=person_detected,
            person_bbox=person_bbox,
            person_center=person_center
        )
    
    def _create_feature_vector(
        self,
        detections: List[Detection],
        frame_shape: Tuple[int, int, int]
    ) -> np.ndarray:
        """
        Create a fixed-size feature vector from detections.
        
        Args:
            detections: List of Detection objects
            frame_shape: (height, width, channels)
        
        Returns:
            numpy array of shape (256,)
        """
        feature_vector = np.zeros(self.feature_size)
        
        # Frame dimensions for normalization
        h, w = frame_shape[:2]
        
        # Track which features we've filled
        idx = 0
        
        # Feature 1: Person detection (0-3)
        person_detected = False
        person_bbox_normalized = [0, 0, 0, 0]
        
        for det in detections:
            if det.class_name == "person" and idx < 4:
                person_detected = True
                # Normalize bbox to [0, 1]
                x, y, bw, bh = det.bbox
                person_bbox_normalized = [
                    x / w,
                    y / h,
                    bw / w,
                    bh / h
                ]
                feature_vector[idx:idx+4] = person_bbox_normalized
                idx += 4
                break
        
        if not person_detected:
            idx = 4
        
        # Feature 2: Object detections (4-19)
        # One-hot encoding for each object type
        object_types = [
            "spray_bottle", "stripping_cup", "teat_cups_attached",
            "teat_cups_detached", "dip_applicator"
        ]
        
        for obj_type in object_types:
            detected = False
            for det in detections:
                if det.class_name == obj_type:
                    detected = True
                    # Add normalized position
                    x, y, bw, bh = det.bbox
                    feature_vector[idx] = 1.0  # Detected
                    feature_vector[idx+1] = x / w  # Normalized x
                    feature_vector[idx+2] = y / h  # Normalized y
                    idx += 3
                    break
            
            if not detected:
                idx += 3
        
        # Feature 3: Detection statistics (20-30)
        if detections:
            confidences = [d.confidence for d in detections]
            feature_vector[idx] = len(detections) / 10.0  # Normalized count
            feature_vector[idx+1] = np.mean(confidences)
            feature_vector[idx+2] = np.max(confidences)
            feature_vector[idx+3] = np.min(confidences)
            idx += 4
        
        # Feature 4: Spatial relationships (30-50)
        if person_detected and len(detections) > 1:
            person_center = None
            for det in detections:
                if det.class_name == "person":
                    person_center = det.center
                    break
            
            if person_center:
                for det in detections:
                    if det.class_name != "person":
                        # Distance from person to object
                        dx = (det.center[0] - person_center[0]) / w
                        dy = (det.center[1] - person_center[1]) / h
                        distance = np.sqrt(dx**2 + dy**2)
                        
                        if idx + 2 < self.feature_size:
                            feature_vector[idx] = dx
                            feature_vector[idx+1] = dy
                            feature_vector[idx+2] = distance
                            idx += 3
        
        # Feature 5: Motion estimation (placeholder for sequence)
        # This would be filled when processing sequences
        
        return feature_vector
    
    def extract_sequence_features(
        self,
        frames: List[np.ndarray]
    ) -> np.ndarray:
        """
        Extract features from a sequence of frames.
        
        Args:
            frames: List of BGR images
        
        Returns:
            numpy array of shape (sequence_length, feature_size)
        """
        sequence_features = []
        
        for frame in frames:
            frame_features = self.extract_features(frame)
            sequence_features.append(frame_features.feature_vector)
        
        # Pad or truncate to sequence_length
        seq_len = self.config.sequence_length if hasattr(self.config, 'sequence_length') else 30
        
        if len(sequence_features) < seq_len:
            # Pad with zeros
            padding = [np.zeros(self.feature_size) for _ in range(seq_len - len(sequence_features))]
            sequence_features.extend(padding)
        elif len(sequence_features) > seq_len:
            # Take last seq_len frames
            sequence_features = sequence_features[-seq_len:]
        
        return np.array(sequence_features)
    
    def get_person_center(self, detections: List[Detection]) -> Optional[Tuple[int, int]]:
        """
        Get the center position of the first person detected.
        
        Args:
            detections: List of Detection objects
        
        Returns:
            (x, y) center of person, or None if not detected
        """
        for det in detections:
            if det.class_name == "person":
                return det.center
        return None
    
    def is_person_in_roi(
        self,
        person_center: Optional[Tuple[int, int]],
        roi: Tuple[int, int, int, int]
    ) -> bool:
        """
        Check if person is within a region of interest.
        
        Args:
            person_center: (x, y) center of person
            roi: (x, y, width, height) region of interest
        
        Returns:
            True if person is in ROI
        """
        if person_center is None:
            return False
        
        x, y = person_center
        roi_x, roi_y, roi_w, roi_h = roi
        
        return (roi_x <= x <= roi_x + roi_w and
                roi_y <= y <= roi_y + roi_h)
