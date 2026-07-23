"""
Import Roboflow YOLO annotations into the training pipeline.

Usage:
  python import_roboflow.py --zip path/to/export.zip
  python import_roboflow.py --folder path/to/export/
  python import_roboflow.py --zip export.zip --val-split 0.2

Roboflow export must be in YOLO format (images/ + labels/ folders).
"""

import os
import sys
import json
import shutil
import random
import zipfile
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATASET_DIR = DATA_DIR / "yolo_dataset"
FRAMES_DIR = DATA_DIR / "frames"

# Must match train_yolo_custom.py classes
CLASSES = ["person", "pipe_sprayer", "stripping_cup", "teat_cup_on", "teat_cup_off", "dip_applicator"]


def find_images_and_labels(source: Path):
    """Find images and labels directories in the source."""
    # Check if source itself contains images/ and labels/
    if (source / "images").is_dir() and (source / "labels").is_dir():
        return source / "images", source / "labels"

    # Check subfolders (Roboflow sometimes nests one level)
    for sub in source.iterdir():
        if sub.is_dir() and (sub / "images").is_dir() and (sub / "labels").is_dir():
            return sub / "images", sub / "labels"

    # Maybe the source IS the images folder
    if any(f.suffix.lower() in (".jpg", ".jpeg", ".png") for f in source.iterdir()):
        return source, source.parent / "labels"

    print(f"Error: Could not find images/ and labels/ in {source}")
    print("Expected structure:")
    print("  export/")
    print("    images/")
    print("    labels/")
    sys.exit(1)


def convert_roboflow_to_annotations(images_dir: Path, labels_dir: Path, output_path: Path):
    """Convert Roboflow YOLO labels to our annotations.json format."""
    annotations = {}
    converted = 0
    skipped = 0

    for img_file in sorted(images_dir.iterdir()):
        if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            continue

        label_file = labels_dir / (img_file.stem + ".txt")
        if not label_file.exists():
            skipped += 1
            continue

        # Read image to get dimensions
        try:
            from PIL import Image
            img = Image.open(img_file)
            w, h = img.size
        except Exception as e:
            print(f"Warning: Could not read {img_file}: {e}")
            skipped += 1
            continue

        boxes = []
        with open(label_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue

                class_id = int(parts[0])
                cx, cy, bw, bh = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])

                # Convert YOLO normalized to absolute xyxy
                x1 = int((cx - bw / 2) * w)
                y1 = int((cy - bh / 2) * h)
                x2 = int((cx + bw / 2) * w)
                y2 = int((cy + bh / 2) * h)

                # Clamp to image bounds
                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(w, x2)
                y2 = min(h, y2)

                boxes.append({
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "class_id": class_id + 1  # Our format uses 1-indexed
                })

        if boxes:
            annotations[str(img_file.resolve())] = {"boxes": boxes}
            converted += 1

    # Save annotations
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(annotations, f, indent=2)

    print(f"Converted {converted} images, skipped {skipped}")
    print(f"Annotations saved to {output_path}")
    return annotations


def build_yolo_dataset(images_dir: Path, labels_dir: Path, val_split: float = 0.15):
    """Build YOLO dataset directly from Roboflow export."""
    # Clear dataset
    for split in ["train", "val"]:
        for sub in ["images", "labels"]:
            d = DATASET_DIR / sub / split
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    # Collect all images with labels
    pairs = []
    for img_file in images_dir.iterdir():
        if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            continue
        label_file = labels_dir / (img_file.stem + ".txt")
        if label_file.exists():
            pairs.append((img_file, label_file))

    print(f"Found {len(pairs)} image-label pairs")

    # Shuffle and split
    random.shuffle(pairs)
    split_idx = int(len(pairs) * (1 - val_split))
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    print(f"Train: {len(train_pairs)}, Val: {len(val_pairs)}")

    # Copy files
    for split_name, split_pairs in [("train", train_pairs), ("val", val_pairs)]:
        for img_path, label_path in split_pairs:
            shutil.copy2(img_path, DATASET_DIR / "images" / split_name / img_path.name)
            shutil.copy2(label_path, DATASET_DIR / "labels" / split_name / label_path.name)

    # Create dataset YAML
    yaml_content = f"""path: {DATASET_DIR.resolve()}
train: images/train
val: images/val

nc: {len(CLASSES)}
names: {CLASSES}
"""
    yaml_path = DATASET_DIR / "dataset.yaml"
    with open(yaml_path, "w") as f:
        f.write(yaml_content)

    print(f"Dataset ready at {yaml_path}")
    return yaml_path


def copy_to_frames(images_dir: Path, labels_dir: Path):
    """Also copy images to data/frames/ for LSTM training."""
    task_dirs = {
        "person": FRAMES_DIR / "task_01_precleaning",
        "pipe_sprayer": FRAMES_DIR / "task_01_precleaning",
        "stripping_cup": FRAMES_DIR / "task_02_stripping",
        "teat_cup_on": FRAMES_DIR / "task_03_attachment",
        "teat_cup_off": FRAMES_DIR / "task_05_detachment",
        "dip_applicator": FRAMES_DIR / "task_06_postdip",
    }

    copied = 0
    for img_file in images_dir.iterdir():
        if img_file.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue

        label_file = labels_dir / (img_file.stem + ".txt")
        if not label_file.exists():
            continue

        # Find dominant class in label
        class_counts = {}
        with open(label_file) as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    cls_id = int(parts[0])
                    class_counts[cls_id] = class_counts.get(cls_id, 0) + 1

        if not class_counts:
            continue

        dominant_class = max(class_counts, key=class_counts.get)
        if dominant_class < len(CLASSES):
            class_name = CLASSES[dominant_class]
            if class_name in task_dirs:
                dst = task_dirs[class_name] / img_file.name
                if not dst.exists():
                    shutil.copy2(img_file, dst)
                    copied += 1

    print(f"Copied {copied} images to {FRAMES_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Import Roboflow YOLO annotations")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip", help="Path to Roboflow export zip file")
    group.add_argument("--folder", help="Path to Roboflow export folder")
    parser.add_argument("--val-split", type=float, default=0.15, help="Validation split ratio")
    parser.add_argument("--also-frames", action="store_true", help="Also copy images to data/frames/ for LSTM training")
    args = parser.parse_args()

    # Handle zip
    if args.zip:
        zip_path = Path(args.zip)
        if not zip_path.exists():
            print(f"Error: {zip_path} not found")
            sys.exit(1)

        extract_dir = DATA_DIR / "roboflow_temp"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)

        print(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # Find the actual export folder (might be nested)
        source = extract_dir
        images_dir, labels_dir = find_images_and_labels(source)
    else:
        source = Path(args.folder)
        if not source.exists():
            print(f"Error: {source} not found")
            sys.exit(1)
        images_dir, labels_dir = find_images_and_labels(source)

    print(f"Images: {images_dir}")
    print(f"Labels: {labels_dir}")

    # Count files
    img_count = len([f for f in images_dir.iterdir() if f.suffix.lower() in (".jpg", ".jpeg", ".png")])
    lbl_count = len([f for f in labels_dir.iterdir() if f.suffix == ".txt"])
    print(f"Found {img_count} images, {lbl_count} labels")

    # Convert to annotations.json
    annotations_path = DATA_DIR / "labels" / "annotations.json"
    convert_roboflow_to_annotations(images_dir, labels_dir, annotations_path)

    # Build YOLO dataset
    build_yolo_dataset(images_dir, labels_dir, args.val_split)

    # Optionally copy to frames
    if args.also_frames:
        copy_to_frames(images_dir, labels_dir)

    # Cleanup temp
    if args.zip and extract_dir.exists():
        shutil.rmtree(extract_dir)
        print("Cleaned up temp files")

    print("\nDone! Next steps:")
    print("  1. Train custom YOLO:  python train_yolo_custom.py")
    print("  2. Copy weights:       python -c \"import shutil; shutil.copy('models/yolov8_milking_custom.pt', '../Monitoring_App/milking-monitor/apps/inference-service/models/')\"")


if __name__ == "__main__":
    main()
