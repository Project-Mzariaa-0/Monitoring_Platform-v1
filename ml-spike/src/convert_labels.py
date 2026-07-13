"""
Convert Roboflow polygon labels to YOLO bounding box format.
"""

import os
from pathlib import Path


def polygon_to_bbox(points):
    """Convert polygon points to YOLO bounding box (x_center, y_center, width, height)."""
    xs = points[0::2]
    ys = points[1::2]
    
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    width = x_max - x_min
    height = y_max - y_min
    
    return x_center, y_center, width, height


def convert_label(input_path, output_path):
    """Convert a single polygon label file to YOLO bbox format."""
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    yolo_lines = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 7:  # class + at least 3 points (6 coords)
            continue
        
        class_id = int(parts[0])
        coords = [float(x) for x in parts[1:]]
        
        # Convert polygon to bbox
        x_center, y_center, width, height = polygon_to_bbox(coords)
        
        # YOLO format: class x_center y_center width height
        yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(yolo_lines))


def main():
    input_dir = Path("data/yolo_dataset/train/labels")
    output_dir = Path("data/yolo_dataset_v2/train/labels")
    images_src = Path("data/yolo_dataset/train/images")
    images_dst = Path("data/yolo_dataset_v2/train/images")
    
    # Create output directories
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dst.mkdir(parents=True, exist_ok=True)
    
    # Convert labels
    converted = 0
    for label_file in input_dir.glob("*.txt"):
        # Convert
        output_file = output_dir / label_file.name
        convert_label(label_file, output_file)
        converted += 1
    
    # Copy images
    for img_file in images_src.glob("*.jpg"):
        import shutil
        shutil.copy2(img_file, images_dst / img_file.name)
    
    print(f"Converted {converted} labels")
    print(f"Output: {output_dir}")
    print(f"Images: {images_dst}")


if __name__ == "__main__":
    main()
