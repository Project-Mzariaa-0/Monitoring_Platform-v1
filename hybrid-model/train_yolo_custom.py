"""
Fine-tune YOLOv8 on milking parlor objects.

Usage:
  1. Run label_tool.py to annotate images
  2. Run: python train_yolo_custom.py

Classes:
  0: person
  1: pipe_sprayer
  2: stripping_cup
  3: teat_cup_on
  4: teat_cup_off
  5: dip_applicator
"""
import os
import json
import random
import shutil
from pathlib import Path
from ultralytics import YOLO

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
FRAMES_DIR = DATA_DIR / "frames"
LABELS_FILE = DATA_DIR / "labels" / "annotations.json"
DATASET_DIR = DATA_DIR / "yolo_dataset"

CLASSES = ["person", "pipe_sprayer", "stripping_cup", "teat_cup_on", "teat_cup_off", "dip_applicator"]
VAL_SPLIT = 0.15


def prepare_dataset():
    if not LABELS_FILE.exists():
        print("No annotations found. Run label_tool.py first.")
        return False

    with open(LABELS_FILE) as f:
        annotations = json.load(f)

    print(f"Found {len(annotations)} annotated images")

    # Clear dataset
    for split in ["train", "val"]:
        for sub in ["images", "labels"]:
            d = DATASET_DIR / sub / split
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True, exist_ok=True)

    items = list(annotations.items())
    random.shuffle(items)
    split_idx = int(len(items) * (1 - VAL_SPLIT))
    train_items = items[:split_idx]
    val_items = items[split_idx:]

    print(f"Train: {len(train_items)}, Val: {len(val_items)}")

    for split_name, split_items in [("train", train_items), ("val", val_items)]:
        for img_path, boxes in split_items:
            if not os.path.exists(img_path):
                continue

            # Copy image
            dst_img = DATASET_DIR / "images" / split_name / os.path.basename(img_path)
            shutil.copy2(img_path, dst_img)

            # Create label file
            label_path = DATASET_DIR / "labels" / split_name / (Path(img_path).stem + ".txt")
            img = __import__("PIL").Image.open(img_path)
            w, h = img.size

            lines = []
            for box in boxes:
                cls = box["class"] - 1
                if cls < 0 or cls >= len(CLASSES):
                    continue
                x1, y1, x2, y2 = box["x1"], box["y1"], box["x2"], box["y2"]
                cx = ((x1 + x2) / 2) / w
                cy = ((y1 + y2) / 2) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                lines.append(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

            with open(label_path, "w") as f:
                f.write("\n".join(lines))

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
    return True


def train():
    yaml_path = DATASET_DIR / "dataset.yaml"
    if not yaml_path.exists():
        print("Dataset not prepared. Run with --prepare first.")
        return

    model = YOLO("yolov8s.pt")

    results = model.train(
        data=str(yaml_path),
        epochs=150,
        imgsz=640,
        batch=16,
        name="milking_custom",
        project=str(BASE_DIR / "models"),
        exist_ok=True,
        patience=20,
        save=True,
        device="cpu",
    )

    best_weights = BASE_DIR / "models" / "milking_custom" / "weights" / "best.pt"
    output_weights = BASE_DIR / "models" / "yolov8_milking_custom.pt"

    if best_weights.exists():
        shutil.copy2(best_weights, output_weights)
        print(f"Training complete. Weights saved to {output_weights}")
    else:
        print("Training complete but best weights not found.")


if __name__ == "__main__":
    import sys
    if "--prepare" in sys.argv:
        prepare_dataset()
    else:
        if prepare_dataset():
            train()
