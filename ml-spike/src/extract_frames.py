"""Extract frames from videos at a given FPS for labeling."""

from __future__ import annotations

import argparse
import cv2
from pathlib import Path


def extract_frames(video_path: Path, output_dir: Path, fps: float = 1.0) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_interval = int(video_fps / fps)
    if frame_interval < 1:
        frame_interval = 1

    frame_idx = 0
    saved = 0
    stem = video_path.stem

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_interval == 0:
            out_path = output_dir / f"{stem}_{saved:05d}.jpg"
            cv2.imwrite(str(out_path), frame)
            saved += 1
        frame_idx += 1

    cap.release()
    return saved


def main():
    parser = argparse.ArgumentParser(description="Extract frames from videos")
    parser.add_argument("videos", nargs="+", type=Path, help="Video files")
    parser.add_argument("--out", type=Path, default=Path("data/frames"), help="Output directory")
    parser.add_argument("--fps", type=float, default=1.0, help="Frames per second to extract")
    args = parser.parse_args()

    for video in args.videos:
        count = extract_frames(video, args.out, args.fps)
        print(f"{video.name}: extracted {count} frames to {args.out}")


if __name__ == "__main__":
    main()
