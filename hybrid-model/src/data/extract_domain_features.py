"""
Enhanced feature extraction using domain knowledge.
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

from config import load_config, ModelConfig
from detection.enhanced_yolo import EnhancedYOLODetector


class DomainFeatureExtractor:
    """
    Feature extractor with domain knowledge about milking process.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the extractor.
        
        Args:
            config: Model configuration with domain knowledge
        """
        self.config = config
        self.detector = EnhancedYOLODetector(config)
    
    def extract_from_video(
        self,
        video_path: str,
        output_path: str,
        target_fps: int = 5
    ) -> np.ndarray:
        """
        Extract features from a video file.
        
        Args:
            video_path: Path to video
            output_path: Path to save features
            target_fps: Target FPS
        
        Returns:
            Features array of shape (num_frames, 512)
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        original_fps = cap.get(cv2.CAP_PROP_FPS)
        frame_skip = max(1, int(original_fps / target_fps))
        
        features = []
        frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx % frame_skip == 0:
                # Don't resize - let YOLO handle native resolution with imgsz=1280
                frame_features = self.detector.extract_features(frame, frame_idx=frame_idx)
                features.append(frame_features.feature_vector)
            
            frame_idx += 1
        
        cap.release()
        
        features_array = np.array(features)
        
        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.save(output_path, features_array)
        
        print(f"Extracted {len(features_array)} frames, shape: {features_array.shape}")
        return features_array
    
    def extract_from_frames(
        self,
        frames_dir: str,
        output_path: str
    ) -> np.ndarray:
        """
        Extract features from a directory of frames.
        
        Args:
            frames_dir: Directory with frame images
            output_path: Path to save features
        
        Returns:
            Features array
        """
        frames_dir = Path(frames_dir)
        frame_files = sorted(frames_dir.glob("*.jpg"))
        
        features = []
        
        for i, frame_file in enumerate(tqdm(frame_files, desc="Extracting features")):
            frame = cv2.imread(str(frame_file))
            if frame is None:
                continue
            
            frame_resized = cv2.resize(frame, (640, 640))
            frame_features = self.detector.extract_features(frame_resized, i)
            features.append(frame_features.feature_vector)
        
        features_array = np.array(features)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        np.save(output_path, features_array)
        
        print(f"Extracted {len(features_array)} frames, shape: {features_array.shape}")
        return features_array


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract domain-aware features")
    parser.add_argument("--input", type=str, required=True,
                        help="Video file or frames directory")
    parser.add_argument("--output", type=str, required=True,
                        help="Output .npy path")
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Config file path")
    parser.add_argument("--fps", type=int, default=5,
                        help="Target FPS for video")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Create extractor
    extractor = DomainFeatureExtractor(config)
    
    # Extract features
    input_path = Path(args.input)
    
    if input_path.is_file():
        # Video file
        extractor.extract_from_video(
            str(input_path),
            args.output,
            target_fps=args.fps
        )
    elif input_path.is_dir():
        # Frames directory
        extractor.extract_from_frames(
            str(input_path),
            args.output
        )
    else:
        raise ValueError(f"Input not found: {input_path}")


if __name__ == "__main__":
    main()
