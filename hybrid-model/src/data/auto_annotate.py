"""
Auto-annotate frames using YOLO + simple heuristics.
Creates initial annotations for training.
"""

import os
import json
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO


def auto_annotate_video(
    frames_dir: str,
    output_path: str,
    model_path: str = "yolov8n.pt",
    fps: int = 5
):
    """
    Auto-annotate frames using YOLO detection.
    
    Args:
        frames_dir: Directory with extracted frames
        output_path: Output JSON path
        model_path: Path to YOLO model
        fps: Frames per second
    """
    # Load YOLO model
    model = YOLO(model_path)
    
    # Get all frames
    frames_dir = Path(frames_dir)
    frame_files = sorted(frames_dir.glob("*.jpg"))
    
    print(f"Annotating {len(frame_files)} frames...")
    
    # Track detections across frames
    task_segments = {
        "TASK-01": [],  # Pre-cleaning (person + spray bottle)
        "TASK-02": [],  # Stripping (person + stripping cup)
        "TASK-03": [],  # Machine attachment (person + cups attached)
        "TASK-04": [],  # Milking (cups attached)
        "TASK-05": [],  # Detachment (cups detached)
        "TASK-06": [],  # Post-dip (person + dip applicator)
    }
    
    # Simple heuristic: assume tasks happen in sequence
    # This is a placeholder - real annotations would be manual
    total_frames = len(frame_files)
    frames_per_task = total_frames // 6
    
    for i, frame_file in enumerate(frame_files):
        # Determine which task based on frame position
        task_idx = min(i // frames_per_task, 5)
        task_id = f"TASK-0{task_idx + 1}"
        
        # Run YOLO to verify person is present
        frame = cv2.imread(str(frame_file))
        results = model(frame, conf=0.3, verbose=False)
        
        person_detected = False
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    if int(box.cls.item()) == 0:  # person class
                        person_detected = True
                        break
        
        # Only add frame if person is detected (for tasks that need person)
        if task_idx in [0, 1, 4, 5] and person_detected:
            task_segments[task_id].append(i)
        elif task_idx in [2, 3]:  # Machine tasks don't always need person visible
            task_segments[task_id].append(i)
    
    # Convert to segments
    annotations = {"tasks": []}
    
    for task_id, frames in task_segments.items():
        if not frames:
            continue
        
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
        
        # Add segments
        for start, end in segments:
            annotations["tasks"].append({
                "id": task_id,
                "start_frame": start,
                "end_frame": end,
                "start_time": round(start / fps, 2),
                "end_time": round(end / fps, 2)
            })
    
    # Save annotations
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(annotations, f, indent=2)
    
    print(f"Created annotations with {len(annotations['tasks'])} task segments")
    return annotations


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-annotate frames")
    parser.add_argument("--frames-dir", type=str, required=True,
                        help="Directory with extracted frames")
    parser.add_argument("--output", type=str, required=True,
                        help="Output JSON path")
    parser.add_argument("--model", type=str, default="yolov8n.pt",
                        help="YOLO model path")
    parser.add_argument("--fps", type=int, default=5,
                        help="Frames per second")
    
    args = parser.parse_args()
    
    auto_annotate_video(
        args.frames_dir,
        args.output,
        args.model,
        args.fps
    )


if __name__ == "__main__":
    main()
