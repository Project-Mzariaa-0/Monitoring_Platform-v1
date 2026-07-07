"""Convert extracted frames + labels into YOLO dataset structure.

Usage:
    1. Extract frames: python extract_frames.py video1.mp4 video2.mp4 --fps 1
    2. Auto-label:     python auto_label.py
    3. Manual review:  Correct labels in data/auto_labels/
    4. Convert:        python convert_to_yolo.py

Creates:
    data/yolo_dataset/
    ├── data.yaml
    ├── train/
    │   ├── images/
    │   └── labels/
    └── val/
        ├── images/
        └── labels/
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path


NAMES = [
    "person",
    "spray_bottle",
    "stripping_cup",
    "teat_cups_attached",
    "teat_cups_detached",
    "dip_applicator",
]


def main():
    parser = argparse.ArgumentParser(description="Build YOLO dataset from frames + labels")
    parser.add_argument("--frames", type=Path, default=Path("data/frames"))
    parser.add_argument("--labels", type=Path, default=Path("data/auto_labels"))
    parser.add_argument("--output", type=Path, default=Path("data/yolo_dataset"))
    parser.add_argument("--val-split", type=float, default=0.2, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    images = sorted(args.frames.glob("*.jpg")) + sorted(args.frames.glob("*.png"))
    if not images:
        print(f"No images found in {args.frames}")
        return

    labeled = [img for img in images if (args.labels / f"{img.stem}.txt").exists()]
    print(f"Found {len(labeled)} labeled frames out of {len(images)} total")

    random.shuffle(labeled)
    val_count = max(1, int(len(labeled) * args.val_split))
    val_set = set(labeled[:val_count])
    train_set = set(labeled[val_count:])

    for split_name, split_set in [("train", train_set), ("val", val_set)]:
        img_dir = args.output / split_name / "images"
        lbl_dir = args.output / split_name / "labels"
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

        for img_path in split_set:
            shutil.copy2(img_path, img_dir / img_path.name)
            lbl_src = args.labels / f"{img_path.stem}.txt"
            if lbl_src.exists():
                shutil.copy2(lbl_src, lbl_dir / f"{img_path.stem}.txt")

        print(f"{split_name}: {len(split_set)} images")

    yaml_content = f"""path: {args.output.resolve()}
train: train/images
val: val/images

nc: {len(NAMES)}
names: {NAMES}
"""
    (args.output / "data.yaml").write_text(yaml_content, encoding="utf-8")
    print(f"\nDataset ready at {args.output}")
    print(f"Config: {args.output / 'data.yaml'}")


if __name__ == "__main__":
    main()
