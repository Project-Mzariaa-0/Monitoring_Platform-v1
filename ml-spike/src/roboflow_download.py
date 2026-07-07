"""Download labeled dataset from Roboflow in YOLOv8 format."""

from __future__ import annotations

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Download Roboflow dataset")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--version", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("data/yolo_dataset"))
    args = parser.parse_args()

    from roboflow import Roboflow
    rf = Roboflow(api_key=args.api_key)
    project = rf.workspace().project(args.project)
    version = project.version(args.version)
    version.download("yolov8", location=str(args.output))

    print(f"Downloaded to {args.output}")
    print(f"Train with: yolo detect train data={args.output}/data.yaml model=yolov8n.pt epochs=100 imgsz=640")


if __name__ == "__main__":
    main()
