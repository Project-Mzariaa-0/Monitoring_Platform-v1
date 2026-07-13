"""
Auto-label unlabeled images using trained model.
"""

import sys
from pathlib import Path
from ultralytics import YOLO

# Load model
model = YOLO("runs/detect/auto_annotate_model/weights/best.pt")

# Directories
images_dir = Path("data/frames")
output_dir = Path("data/auto_labeled")
output_dir.mkdir(exist_ok=True)

# Get all images
image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
all_images = [f for f in images_dir.iterdir() if f.suffix.lower() in image_exts]

# Filter out already labeled images
labeled_dir = Path("data/yolo_dataset_v2/train/labels")
labeled_stems = {f.stem for f in labeled_dir.glob("*.txt")}

# Map back to original image names (Roboflow renamed them)
# We'll just label all and skip if label exists
unlabeled = [f for f in all_images if f.stem not in labeled_stems]

print(f"Total images: {len(all_images)}")
print(f"Already labeled: {len(labeled_stems)}")
print(f"To auto-label: {len(unlabeled)}")

# Auto-label
labeled_count = 0
total_detections = 0

for i, img_path in enumerate(unlabeled):
    # Run inference
    results = model(str(img_path), conf=0.3, verbose=False)
    
    if results and len(results) > 0:
        result = results[0]
        
        if len(result.boxes) > 0:
            # Get image dimensions
            img_h, img_w = result.orig_shape
            
            # Convert to YOLO format
            labels = []
            for box in result.boxes:
                cls = int(box.cls[0])
                x_center, y_center, width, height = box.xywhn[0].tolist()
                conf = float(box.conf[0])
                
                # YOLO format: class x_center y_center width height
                labels.append(f"{cls} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
            
            # Save label file
            label_path = output_dir / f"{img_path.stem}.txt"
            with open(label_path, "w") as f:
                f.write("\n".join(labels))
            
            # Copy image
            import shutil
            shutil.copy2(img_path, output_dir / img_path.name)
            
            labeled_count += 1
            total_detections += len(result.boxes)
    
    if (i + 1) % 50 == 0:
        print(f"  Processed {i + 1}/{len(unlabeled)} images...")

print(f"\nDone!")
print(f"Auto-labeled: {labeled_count} images")
print(f"Total detections: {total_detections}")
print(f"Output: {output_dir}")
