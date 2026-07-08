"""
Auto-Annotation Pipeline for Milking Monitor
Uses YOLO + SAM to quickly annotate images for training.

Usage:
    python auto_annotate.py --input data/raw --output data/labeled --classes person,spray_bottle,teat_cups
"""

import os
import sys
import argparse
import subprocess
import json
from pathlib import Path
from typing import List, Dict
import shutil

# Class mapping for milking-specific objects
MILKING_CLASSES = {
    "person": 0,
    "spray_bottle": 1,
    "stripping_cup": 2,
    "teat_cups_attached": 3,
    "teat_cups_detached": 4,
    "dip_applicator": 5,
    "cow": 6,
    "milking_machine": 7,
}


def check_dependencies():
    """Check if required packages are installed."""
    required = ["ultralytics", "PIL"]
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Installing missing packages: {missing}")
        subprocess.run([sys.executable, "-m", "pip", "install", "ultralytics", "Pillow"], check=True)


def train_initial_model(
    labeled_dir: str,
    classes: List[str],
    epochs: int = 50,
    imgsz: int = 640
) -> str:
    """
    Train a quick YOLO model on manually labeled images.
    
    Args:
        labeled_dir: Directory with labeled images and labels
        classes: List of class names to detect
        epochs: Number of training epochs
        imgsz: Image size for training
    
    Returns:
        Path to trained model
    """
    from ultralytics import YOLO
    
    # Create dataset config
    dataset_config = create_dataset_config(labeled_dir, classes)
    config_path = Path(labeled_dir) / "dataset.yaml"
    
    with open(config_path, "w") as f:
        f.write(dataset_config)
    
    print(f"Training initial model on {count_images(labeled_dir)} images...")
    
    # Train YOLOv8 nano (fast)
    model = YOLO("yolov8n.pt")
    results = model.train(
        data=str(config_path),
        epochs=epochs,
        imgsz=imgsz,
        batch=8,
        name="auto_annotate_model",
        patience=20,
        verbose=True
    )
    
    # Find best model
    runs_dir = Path("runs/detect/auto_annotate_model")
    best_model = runs_dir / "weights" / "best.pt"
    
    if best_model.exists():
        print(f"Model trained: {best_model}")
        return str(best_model)
    else:
        raise FileNotFoundError(f"Model not found at {best_model}")


def auto_label_with_model(
    model_path: str,
    images_dir: str,
    output_dir: str,
    confidence: float = 0.25
) -> int:
    """
    Use trained model to auto-label unlabeled images.
    
    Args:
        model_path: Path to trained YOLO model
        images_dir: Directory with unlabeled images
        output_dir: Directory to save labels
        confidence: Confidence threshold for detections
    
    Returns:
        Number of images labeled
    """
    from ultralytics import YOLO
    import cv2
    
    model = YOLO(model_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Get all images
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    images = [
        f for f in Path(images_dir).iterdir()
        if f.suffix.lower() in image_extensions
    ]
    
    print(f"Auto-labeling {len(images)} images...")
    
    labeled_count = 0
    for img_path in images:
        # Run inference
        results = model(str(img_path), conf=confidence, verbose=False)
        
        if results and len(results) > 0:
            result = results[0]
            
            if len(result.boxes) > 0:
                # Convert to YOLO format
                img_h, img_w = result.orig_shape
                
                labels = []
                for box in result.boxes:
                    cls = int(box.cls[0])
                    x_center, y_center, width, height = box.xywhn[0].tolist()
                    conf = float(box.conf[0])
                    
                    # YOLO format: class x_center y_center width height
                    labels.append(f"{cls} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                
                # Save label file
                label_path = output_path / f"{img_path.stem}.txt"
                with open(label_path, "w") as f:
                    f.write("\n".join(labels))
                
                labeled_count += 1
        
        if labeled_count % 50 == 0:
            print(f"  Labeled {labeled_count}/{len(images)} images...")
    
    print(f"Auto-labeled {labeled_count} images with {len(result.boxes)} total detections")
    return labeled_count


def auto_label_with_grounding(
    images_dir: str,
    output_dir: str,
    prompts: List[str],
    confidence: float = 0.25
) -> int:
    """
    Use Grounding DINO for zero-shot auto-labeling without training.
    Requires: pip install autodistill autodistill-grounded-sam autodistill-yolov8
    
    Args:
        images_dir: Directory with images
        output_dir: Directory to save labels
        prompts: Text prompts for detection
        confidence: Confidence threshold
    
    Returns:
        Number of images labeled
    """
    try:
        from autodistill_grounded_sam import GroundedSAM
        from autodistill.detection import CaptionOntology
    except ImportError:
        print("Installing autodistill packages...")
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "autodistill", "autodistill-grounded-sam", "autodistill-yolov8"
        ], check=True)
        from autodistill_grounded_sam import GroundedSAM
        from autodistill.detection import CaptionOntology
    
    # Create ontology from prompts
    ontology = CaptionOntology({
        prompt: i for i, prompt in enumerate(prompts)
    })
    
    print(f"Auto-labeling with Grounding DINO...")
    print(f"Prompts: {prompts}")
    
    # Initialize model
    model = GroundedSAM(ontology=ontology)
    
    # Label images
    dataset = model.label(
        input_folder=images_dir,
        output_folder=output_dir,
        extension=".jpg",
        confidence=confidence
    )
    
    print(f"Auto-labeled {len(dataset)} images")
    return len(dataset)


def create_dataset_config(dataset_dir: str, classes: List[str]) -> str:
    """Create YOLO dataset config YAML."""
    class_dict = {i: cls for i, cls in enumerate(classes)}
    
    return f"""# Auto-generated dataset config
path: {os.path.abspath(dataset_dir)}
train: images
val: images

# Classes
names:
{chr(10).join(f'  {i}: {cls}' for i, cls in enumerate(classes))}
"""


def count_images(directory: str) -> int:
    """Count images in directory."""
    image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    return len([
        f for f in Path(directory).iterdir()
        if f.suffix.lower() in image_extensions
    ])


def split_dataset(
    labeled_dir: str,
    output_dir: str,
    train_ratio: float = 0.8
):
    """Split labeled dataset into train/val."""
    labeled_path = Path(labeled_dir)
    output_path = Path(output_dir)
    
    # Create directories
    for split in ["train", "val"]:
        (output_path / split / "images").mkdir(parents=True, exist_ok=True)
        (output_path / split / "labels").mkdir(parents=True, exist_ok=True)
    
    # Get all images with labels
    images = [
        f for f in labeled_path.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png"}
        and (labeled_path / f"{f.stem}.txt").exists()
    ]
    
    # Shuffle and split
    import random
    random.shuffle(images)
    
    split_idx = int(len(images) * train_ratio)
    train_images = images[:split_idx]
    val_images = images[split_idx:]
    
    # Copy files
    for img in train_images:
        shutil.copy2(img, output_path / "train" / "images" / img.name)
        shutil.copy2(
            labeled_path / f"{img.stem}.txt",
            output_path / "train" / "labels" / f"{img.stem}.txt"
        )
    
    for img in val_images:
        shutil.copy2(img, output_path / "val" / "images" / img.name)
        shutil.copy2(
            labeled_path / f"{img.stem}.txt",
            output_path / "val" / "labels" / f"{img.stem}.txt"
        )
    
    print(f"Split: {len(train_images)} train, {len(val_images)} val")
    
    # Create dataset config
    classes = list(MILKING_CLASSES.keys())
    config = f"""path: {os.path.abspath(output_path)}
train: train/images
val: val/images

names:
{chr(10).join(f'  {i}: {cls}' for i, cls in enumerate(classes))}
"""
    
    config_path = output_path / "dataset.yaml"
    with open(config_path, "w") as f:
        f.write(config)
    
    print(f"Dataset config saved: {config_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-annotate images for YOLO training")
    parser.add_argument("--input", "-i", required=True, help="Input images directory")
    parser.add_argument("--output", "-o", default="data/labeled", help="Output directory")
    parser.add_argument("--method", choices=["model", "grounding"], default="model",
                       help="Annotation method: 'model' (train first) or 'grounding' (zero-shot)")
    parser.add_argument("--classes", nargs="+", default=list(MILKING_CLASSES.keys()),
                       help="Class names to detect")
    parser.add_argument("--epochs", type=int, default=50, help="Training epochs (model method)")
    parser.add_argument("--confidence", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--split", action="store_true", help="Split into train/val after labeling")
    parser.add_argument("--split-dir", default="data/split", help="Output directory for split")
    
    args = parser.parse_args()
    
    # Check dependencies
    check_dependencies()
    
    # Ensure output directory exists
    Path(args.output).mkdir(parents=True, exist_ok=True)
    
    if args.method == "model":
        # Train then auto-label
        print("=" * 60)
        print("STEP 1: Training initial model on labeled images")
        print("=" * 60)
        
        model_path = train_initial_model(
            args.input,
            args.classes,
            epochs=args.epochs
        )
        
        print("\n" + "=" * 60)
        print("STEP 2: Auto-labeling remaining images")
        print("=" * 60)
        
        labeled_count = auto_label_with_model(
            model_path,
            args.input,
            args.output,
            confidence=args.confidence
        )
        
    else:
        # Zero-shot with Grounding DINO
        print("=" * 60)
        print("Auto-labeling with Grounding DINO (zero-shot)")
        print("=" * 60)
        
        prompts = [cls.replace("_", " ") for cls in args.classes]
        labeled_count = auto_label_with_grounding(
            args.input,
            args.output,
            prompts,
            confidence=args.confidence
        )
    
    # Split dataset if requested
    if args.split:
        print("\n" + "=" * 60)
        print("STEP 3: Splitting dataset")
        print("=" * 60)
        
        split_dataset(args.output, args.split_dir)
    
    print("\n" + "=" * 60)
    print("DONE!")
    print(f"Labeled images: {args.output}")
    if args.split:
        print(f"Split dataset: {args.split_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
