# Auto-Annotation Pipeline

Fast annotation for 400+ images using YOLO.

## Quick Start (Recommended)

### Option 1: Few-Shot Learning (Fastest)

```bash
# Step 1: Select 25 images for manual annotation
python src/quick_annotate.py --raw-dir data/raw --num-samples 25

# Step 2: Manually annotate the 25 images in data/manual/
# Use LabelImg, Roboflow, or any YOLO-compatible tool

# Step 3: Train a quick model
python src/auto_annotate.py --input data/manual --output data/auto_labeled --epochs 50

# Step 4: Merge and create final dataset
python src/quick_annotate.py --raw-dir data/raw --labeled-dir data/manual --auto-dir data/auto_labeled --merge --output data/final

# Step 5: Train final model
yolo detect train data=data/final/dataset.yaml epochs=100 imgsz=640
```

### Option 2: Zero-Shot (No Training)

Requires Grounding DINO (slower but no manual annotation):

```bash
python src/auto_annotate.py --input data/raw --output data/labeled --method grounding --classes person spray_bottle teat_cups
```

## Requirements

```bash
pip install ultralytics Pillow
```

For zero-shot method:
```bash
pip install autodistill autodistill-grounded-sam autodistill-yolov8
```

## Directory Structure

```
data/
├── raw/                    # Your 400 raw images
├── manual/                 # 25 manually annotated images
├── auto_labeled/           # Auto-labeled by model
└── final/                  # Merged dataset for training
    ├── images/
    ├── labels/
    └── dataset.yaml
```

## Annotation Tools

- **LabelImg**: `pip install labelImg && labelImg`
- **Roboflow**: https://roboflow.com (free tier available)
- **CVAT**: https://cvat.ai (open source)

## Tips

1. Start with 25-30 diverse images (different angles, lighting)
2. Include edge cases (partial views, occlusions)
3. Review auto-labels before final training
4. Iterate: train → auto-label → review → retrain
