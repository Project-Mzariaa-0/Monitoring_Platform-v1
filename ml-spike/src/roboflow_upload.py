"""Upload frames to Roboflow for labeling."""

from __future__ import annotations

import argparse
from pathlib import Path


def upload_frames(frames_dir: Path, api_key: str, project_name: str, split: str = "train"):
    from roboflow import Roboflow

    rf = Roboflow(api_key=api_key)
    workspace = rf.workspace()

    # List available projects
    projects = workspace.projects()
    print("Available projects:")
    for p in projects:
        print(f"  - {p}")
    print()

    project = workspace.project(project_name)

    images = sorted(frames_dir.glob("*.jpg")) + sorted(frames_dir.glob("*.png"))
    print(f"Uploading {len(images)} frames to '{project_name}'...")

    for i, img_path in enumerate(images):
        project.upload(str(img_path), split=split)
        if (i + 1) % 10 == 0:
            print(f"  Uploaded {i + 1}/{len(images)}")

    print(f"Done. Go to https://app.roboflow.com to label your frames.")


def main():
    parser = argparse.ArgumentParser(description="Upload frames to Roboflow")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--project", default=None, help="Project name (omit to list available)")
    parser.add_argument("--frames", type=Path, default=Path("data/frames"))
    parser.add_argument("--split", default="train")
    args = parser.parse_args()

    from roboflow import Roboflow
    rf = Roboflow(api_key=args.api_key)
    workspace = rf.workspace()

    if not args.project:
        print("Available projects:")
        for p in workspace.projects():
            print(f"  - {p}")
        print("\nRun again with --project \"PROJECT NAME\"")
        return

    upload_frames(args.frames, args.api_key, args.project, args.split)


if __name__ == "__main__":
    main()
