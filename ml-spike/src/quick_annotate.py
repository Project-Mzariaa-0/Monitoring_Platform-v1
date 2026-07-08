"""
Quick Few-Shot Auto-Annotation
The fastest way to annotate 400 images:
1. Manually label 20-30 images
2. Train a quick model (5 min)
3. Auto-label the rest (automated)
4. Review corrections (30 min)

Usage:
    python quick_annotate.py --raw-dir data/raw --labeled-dir data/manual --output data/final
"""

import os
import sys
import argparse
import shutil
import random
from pathlib import Path
from typing import List, Tuple


# Milking classes
CLASSES = [
    "person",
    "spray_bottle",
    "stripping_cup",
    "teat_cups_attached",
    "teat_cups_detached",
    "dip_applicator",
]


def count_images(directory: Path) -> int:
    """Count images in directory."""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return len([f for f in directory.iterdir() if f.suffix.lower() in exts])


def split_images(
    raw_dir: Path,
    manual_dir: Path,
    num_samples: int = 25
) -> Tuple[List[Path], List[Path]]:
    """
    Randomly select images for manual annotation.
    Returns: (to_annotate, to_auto_label)
    """
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    all_images = [f for f in raw_dir.iterdir() if f.suffix.lower() in exts]
    
    if len(all_images) < num_samples:
        print(f"Warning: Only {len(all_images)} images found, using all")
        num_samples = len(all_images)
    
    random.shuffle(all_images)
    
    to_annotate = all_images[:num_samples]
    to_auto_label = all_images[num_samples:]
    
    # Create manual directory
    manual_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy images for manual annotation
    for img in to_annotate:
        shutil.copy2(img, manual_dir / img.name)
    
    print(f"Selected {len(to_annotate)} images for manual annotation")
    print(f"Remaining {len(to_auto_label)} images will be auto-labeled")
    print(f"\nManual images saved to: {manual_dir}")
    print("\nNEXT STEPS:")
    print(f"1. Open {manual_dir} in a labeling tool (LabelImg, Roboflow, etc.)")
    print(f"2. Annotate all {len(to_annotate)} images")
    print(f"3. Run: python auto_annotate.py --input {manual_dir} --output data/auto_labeled --method model")
    print(f"4. Then: python quick_annotate.py --raw-dir {raw_dir} --manual-dir {manual_dir} --auto-dir data/auto_labeled --merge")
    
    return to_annotate, to_auto_label


def merge_labels(
    manual_dir: Path,
    auto_dir: Path,
    output_dir: Path
):
    """Merge manual and auto-labeled datasets."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy manual labels
    manual_count = 0
    for f in manual_dir.iterdir():
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            shutil.copy2(f, output_dir / f.name)
            label_file = manual_dir / f"{f.stem}.txt"
            if label_file.exists():
                shutil.copy2(label_file, output_dir / f"{f.stem}.txt")
                manual_count += 1
    
    # Copy auto labels
    auto_count = 0
    for f in auto_dir.iterdir():
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            if not (output_dir / f.name).exists():
                shutil.copy2(f, output_dir / f.name)
                label_file = auto_dir / f"{f.stem}.txt"
                if label_file.exists():
                    shutil.copy2(label_file, output_dir / f"{f.stem}.txt")
                    auto_count += 1
    
    print(f"\nMerged dataset:")
    print(f"  Manual labels: {manual_count}")
    print(f"  Auto labels: {auto_count}")
    print(f"  Total: {manual_count + auto_count}")
    print(f"  Output: {output_dir}")


def create_training_config(output_dir: Path):
    """Create YOLO training config."""
    config = f"""path: {os.path.abspath(output_dir)}
train: .
val: .

names:
  0: person
  1: spray_bottle
  2: stripping_cup
  3: teat_cups_attached
  4: teat_cups_detached
  5: dip_applicator
"""
    
    config_path = output_dir / "dataset.yaml"
    with open(config_path, "w") as f:
        f.write(config)
    
    print(f"Training config saved: {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Quick few-shot annotation pipeline")
    parser.add_argument("--raw-dir", required=True, help="Directory with all raw images")
    parser.add_argument("--labeled-dir", default="data/manual", help="Output for manual annotation")
    parser.add_argument("--auto-dir", default="data/auto_labeled", help="Auto-labeled output")
    parser.add_argument("--output", default="data/final", help="Final merged dataset")
    parser.add_argument("--num-samples", type=int, default=25, help="Images to manually annotate")
    parser.add_argument("--merge", action="store_true", help="Merge manual and auto labels")
    
    args = parser.parse_args()
    
    raw_dir = Path(args.raw_dir)
    manual_dir = Path(args.labeled_dir)
    auto_dir = Path(args.auto_dir)
    output_dir = Path(args.output)
    
    if not raw_dir.exists():
        print(f"Error: Raw directory not found: {raw_dir}")
        return
    
    if args.merge:
        # Merge mode
        if not manual_dir.exists():
            print(f"Error: Manual directory not found: {manual_dir}")
            return
        if not auto_dir.exists():
            print(f"Error: Auto directory not found: {auto_dir}")
            return
        
        merge_labels(manual_dir, auto_dir, output_dir)
        create_training_config(output_dir)
        
    else:
        # Initial split mode
        print("=" * 60)
        print("QUICK ANNOTATION PIPELINE")
        print("=" * 60)
        print(f"\nTotal images: {count_images(raw_dir)}")
        print(f"Manual samples: {args.num_samples}")
        print(f"Auto-label rest: {count_images(raw_dir) - args.num_samples}")
        
        split_images(raw_dir, manual_dir, args.num_samples)


if __name__ == "__main__":
    main()
