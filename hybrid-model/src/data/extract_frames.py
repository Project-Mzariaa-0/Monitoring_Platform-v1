"""
Data preparation script for extracting frames from videos.
"""

import os
import json
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
import argparse
from tqdm import tqdm


def extract_frames_from_video(
    video_path: str,
    output_dir: str,
    target_fps: int = 5,
    frame_size: Tuple[int, int] = (640, 640)
) -> int:
    """
    Extract frames from a video file.
    
    Args:
        video_path: Path to input video
        output_dir: Directory to save frames
        target_fps: Target frames per second
        frame_size: Target frame size (width, height)
    
    Returns:
        Number of frames extracted
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}")
        return 0
    
    # Get video info
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Calculate frame skip
    frame_skip = max(1, int(original_fps / target_fps))
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    frame_count = 0
    extracted_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Extract frame at target FPS
        if frame_count % frame_skip == 0:
            # Resize frame
            frame_resized = cv2.resize(frame, frame_size)
            
            # Save frame
            frame_path = os.path.join(output_dir, f"{extracted_count:04d}.jpg")
            cv2.imwrite(frame_path, frame_resized)
            
            extracted_count += 1
        
        frame_count += 1
    
    cap.release()
    
    return extracted_count


def create_annotations_from_labels(
    labels_dir: str,
    output_path: str,
    fps: int = 5
):
    """
    Create annotation JSON from YOLO format labels.
    
    Args:
        labels_dir: Directory with YOLO label files
        output_path: Output JSON path
        fps: Frames per second
    """
    annotations = {"tasks": []}
    
    # Load all label files
    label_files = sorted(Path(labels_dir).glob("*.txt"))
    
    if not label_files:
        print(f"No label files found in {labels_dir}")
        return
    
    # Group labels by task
    task_frames = {}
    
    for label_file in label_files:
        frame_idx = int(label_file.stem)
        
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    class_id = int(parts[0])
                    
                    # Map class to task
                    task_map = {
                        0: "TASK-06",  # person (post-dip context)
                        1: "TASK-01",  # spray_bottle
                        2: "TASK-02",  # stripping_cup
                        3: "TASK-03",  # teat_cups_attached
                        4: "TASK-04",  # teat_cups_detached (milking)
                        5: "TASK-05",  # dip_applicator
                    }
                    
                    if class_id in task_map:
                        task_id = task_map[class_id]
                        if task_id not in task_frames:
                            task_frames[task_id] = []
                        task_frames[task_id].append(frame_idx)
    
    # Create task segments
    for task_id, frames in task_frames.items():
        if frames:
            # Find continuous segments
            frames.sort()
            segments = []
            start = frames[0]
            prev = frames[0]
            
            for frame in frames[1:]:
                if frame - prev > 5:  # Gap > 1 second
                    segments.append((start, prev))
                    start = frame
                prev = frame
            segments.append((start, prev))
            
            # Add segments to annotations
            for start, end in segments:
                annotations["tasks"].append({
                    "id": task_id,
                    "start_frame": start,
                    "end_frame": end,
                    "start_time": start / fps,
                    "end_time": end / fps
                })
    
    # Save annotations
    with open(output_path, 'w') as f:
        json.dump(annotations, f, indent=2)
    
    print(f"Created annotations with {len(annotations['tasks'])} tasks")


def split_dataset(
    data_dir: str,
    output_dir: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1
):
    """
    Split dataset into train/val/test sets.
    
    Args:
        data_dir: Path to processed data directory
        output_dir: Path to splits directory
        train_ratio: Training set ratio
        val_ratio: Validation set ratio
        test_ratio: Test set ratio
    """
    # Get all video directories
    video_dirs = [
        d.name for d in Path(data_dir).iterdir()
        if d.is_dir() and (d / "frames").exists()
    ]
    
    # Shuffle
    np.random.shuffle(video_dirs)
    
    # Split
    n = len(video_dirs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    
    train_videos = video_dirs[:n_train]
    val_videos = video_dirs[n_train:n_train + n_val]
    test_videos = video_dirs[n_train + n_val:]
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Save splits
    for split_name, videos in [("train", train_videos), ("val", val_videos), ("test", test_videos)]:
        split_file = os.path.join(output_dir, f"{split_name}.txt")
        with open(split_file, 'w') as f:
            for video in videos:
                f.write(f"{video}\n")
    
    print(f"Dataset split:")
    print(f"  Train: {len(train_videos)} videos")
    print(f"  Val: {len(val_videos)} videos")
    print(f"  Test: {len(test_videos)} videos")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Prepare dataset for training")
    parser.add_argument("--input", type=str, required=True,
                        help="Input directory with videos")
    parser.add_argument("--output", type=str, default="data/processed",
                        help="Output directory for processed data")
    parser.add_argument("--fps", type=int, default=5,
                        help="Target FPS for frame extraction")
    parser.add_argument("--frame-size", type=int, nargs=2, default=[640, 640],
                        help="Target frame size (width height)")
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    # Process each video
    video_files = list(input_dir.glob("*.mp4")) + list(input_dir.glob("*.avi"))
    
    print(f"Found {len(video_files)} videos")
    
    for video_file in tqdm(video_files, desc="Processing videos"):
        video_name = video_file.stem
        video_output_dir = output_dir / video_name / "frames"
        
        # Extract frames
        num_frames = extract_frames_from_video(
            str(video_file),
            str(video_output_dir),
            target_fps=args.fps,
            frame_size=tuple(args.frame_size)
        )
        
        # Create annotations if labels exist
        labels_dir = input_dir / video_name / "labels"
        if labels_dir.exists():
            annotations_path = output_dir / video_name / "annotations.json"
            create_annotations_from_labels(
                str(labels_dir),
                str(annotations_path),
                fps=args.fps
            )
    
    # Split dataset
    splits_dir = output_dir.parent / "splits"
    split_dataset(str(output_dir), str(splits_dir))
    
    print("Data preparation complete!")


if __name__ == "__main__":
    main()
