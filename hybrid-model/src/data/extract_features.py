"""
Pre-extract YOLO features from frames for faster LSTM training.
"""

import os
import json
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO
from tqdm import tqdm
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import load_config


def extract_features_for_video(
    frames_dir: str,
    output_path: str,
    model_path: str = "yolov8n.pt",
    sequence_length: int = 30
):
    """
    Extract YOLO features from all frames and save as numpy array.
    
    Args:
        frames_dir: Directory with frames
        output_path: Output .npy path
        model_path: YOLO model path
        sequence_length: Sequence length for LSTM
    """
    # Load YOLO model
    model = YOLO(model_path)
    
    # Get all frames
    frames_dir = Path(frames_dir)
    frame_files = sorted(frames_dir.glob("*.jpg"))
    
    print(f"Extracting features from {len(frame_files)} frames...")
    
    features = []
    
    for frame_file in tqdm(frame_files, desc="Extracting features"):
        # Load frame
        frame = cv2.imread(str(frame_file))
        
        # Run YOLO
        results = model(frame, conf=0.3, verbose=False)
        
        # Create feature vector (256 dims)
        feature_vector = np.zeros(256)
        
        # Person detection features (0-3)
        person_detected = False
        h, w = frame.shape[:2]
        
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    cls_id = int(box.cls.item())
                    if cls_id == 0:  # person
                        person_detected = True
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        feature_vector[0] = 1.0  # detected
                        feature_vector[1] = x1 / w  # normalized x
                        feature_vector[2] = y1 / h  # normalized y
                        feature_vector[3] = (x2 - x1) / w  # normalized width
                        break
        
        # Object detection features (4-19)
        # Placeholder: in real scenario, use custom model
        feature_vector[4] = 1.0 if person_detected else 0.0
        
        # Detection statistics (20-23)
        num_detections = 0
        for result in results:
            if result.boxes is not None:
                num_detections = len(result.boxes)
        
        feature_vector[20] = min(num_detections / 10.0, 1.0)
        
        features.append(feature_vector)
    
    # Convert to numpy array
    features_array = np.array(features)
    
    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    np.save(output_path, features_array)
    
    print(f"Saved features: {features_array.shape}")
    return features_array


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pre-extract YOLO features")
    parser.add_argument("--data-dir", type=str, default="data/processed",
                        help="Directory with processed data")
    parser.add_argument("--output-dir", type=str, default="data/features",
                        help="Output directory for features")
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                        help="YOLO model path")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    # Process each video
    for video_dir in data_dir.iterdir():
        if not video_dir.is_dir():
            continue
        
        frames_dir = video_dir / "frames"
        if not frames_dir.exists():
            continue
        
        print(f"\nProcessing {video_dir.name}...")
        
        output_path = output_dir / f"{video_dir.name}_features.npy"
        extract_features_for_video(
            str(frames_dir),
            str(output_path),
            args.model
        )
    
    print("\nFeature extraction complete!")


if __name__ == "__main__":
    main()
