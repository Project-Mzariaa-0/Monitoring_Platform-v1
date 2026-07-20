"""
Extract frames from new video clips using OpenCV.

Usage:
  python add_clip.py <video_path> <task_id> [--interval 0.5]

Task IDs:
  1 = pre_cleaning
  2 = stripping
  3 = machine_attachment
  4 = milking
  5 = detachment
  6 = post_dip
"""
import os
import sys
import argparse
import shutil
from pathlib import Path

try:
    import cv2
except ImportError:
    print("opencv-python not installed. Run: pip install opencv-python")
    sys.exit(1)

BASE_DIR = Path(__file__).parent
FRAMES_DIR = BASE_DIR / "data" / "frames"
RAW_DIR = BASE_DIR / "data" / "raw"

TASK_NAMES = {
    1: "task_01_precleaning",
    2: "task_02_stripping",
    3: "task_03_attachment",
    4: "task_04_milking",
    5: "task_05_detachment",
    6: "task_06_postdip",
}


def extract_frames(video_path: str, task_id: int, interval: float = 0.5):
    if task_id not in TASK_NAMES:
        print(f"Invalid task_id: {task_id}. Must be 1-6.")
        return

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return

    task_name = TASK_NAMES[task_id]
    output_dir = FRAMES_DIR / task_name
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy video to raw folder if not already there
    raw_dest = RAW_DIR / video_path.name
    if not raw_dest.exists():
        shutil.copy2(video_path, raw_dest)
        print(f"Copied video to {raw_dest}")

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"Video: {video_path.name}")
    print(f"FPS: {fps:.1f}, Duration: {duration:.1f}s, Total frames: {total_frames}")
    print(f"Task: {task_name}")
    print(f"Interval: {interval}s (extracting every {int(fps * interval)} frames)")
    print(f"Output: {output_dir}")

    # Extract frames
    clip_name = video_path.stem
    frame_interval = int(fps * interval)
    if frame_interval < 1:
        frame_interval = 1

    frame_idx = 0
    extracted = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            filename = f"{clip_name}_frame_{extracted:06d}.jpg"
            cv2.imwrite(str(output_dir / filename), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            extracted += 1

        frame_idx += 1

    cap.release()

    total_in_task = len(list(output_dir.glob("*.jpg")))
    print(f"\nExtracted {extracted} frames from this clip")
    print(f"Total frames in {task_name}: {total_in_task}")


def list_clips():
    print("Existing clips in raw folder:")
    for f in sorted(RAW_DIR.rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(RAW_DIR)} ({f.stat().st_size / 1024 / 1024:.1f} MB)")

    print("\nFrames per task:")
    for task_id, task_name in TASK_NAMES.items():
        task_dir = FRAMES_DIR / task_name
        if task_dir.exists():
            count = len(list(task_dir.glob("*.jpg")))
            print(f"  {task_name}: {count} frames")
        else:
            print(f"  {task_name}: 0 frames")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from video clips")
    parser.add_argument("video", nargs="?", help="Path to video file")
    parser.add_argument("task", nargs="?", type=int, help="Task ID (1-6)")
    parser.add_argument("--interval", type=float, default=0.5, help="Seconds between frames (default: 0.5)")
    parser.add_argument("--list", action="store_true", help="List existing clips and frame counts")

    args = parser.parse_args()

    if args.list:
        list_clips()
    elif args.video and args.task:
        extract_frames(args.video, args.task, args.interval)
    else:
        print("Usage:")
        print('  python add_clip.py "C:/path/to/video.mp4" <task_id>')
        print("  python add_clip.py --list")
        print("\nTask IDs: 1=pre_cleaning, 2=stripping, 3=attachment, 4=milking, 5=detachment, 6=post_dip")
