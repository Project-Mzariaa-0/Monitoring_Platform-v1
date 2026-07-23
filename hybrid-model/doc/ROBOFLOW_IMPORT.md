# Importing Data from Roboflow

This guide explains how to import annotated images from Roboflow into the training pipeline.

## Overview

```
Roboflow (annotate) → Export (YOLO format) → import_roboflow.py → train_yolo_custom.py → Custom YOLO
```

## Step 1: Annotate in Roboflow

### Classes to Use

| ID | Class Name | What to Annotate |
|----|------------|------------------|
| 0 | person | Worker in the milking parlor |
| 1 | pipe_sprayer | Water pipe/sprayer held by person (TASK-01) |
| 2 | stripping_cup | Handheld stripping device (TASK-02) |
| 3 | teat_cup_on | Milking cups attached to cow udder (TASK-03/04) |
| 4 | teat_cup_off | Cups dangling in holder after detachment (TASK-05) |
| 5 | dip_applicator | Cup/applicator for post-dip (TASK-06) |

### Annotation Tips

- Label ALL visible instances, not just obvious ones
- Include different angles, lighting conditions, and cow positions
- For small objects (cups, pipes), draw tight bounding boxes
- For `teat_cup_on`, annotate each cup individually
- For `teat_cup_off`, annotate cups in the holder
- The more consistent your labels, the better the model will learn

### Recommended: At Least 50-100 Images Per Class

| Class | Min Images | Notes |
|-------|------------|-------|
| person | 100 | Easiest to collect, most frames have persons |
| pipe_sprayer | 50 | TASK-01 clips |
| stripping_cup | 50 | TASK-02 clips |
| teat_cup_on | 50 | TASK-03/04 clips |
| teat_cup_off | 50 | TASK-05 clips |
| dip_applicator | 50 | TASK-06 clips |

## Step 2: Export from Roboflow

1. Go to your Roboflow project
2. Click **Generate** → select **YOLO v5 PyTorch** format
3. Click **Download** → choose **zip** format
4. Save the zip file (e.g., `roboflow_export.zip`)

The export will contain:
```
roboflow_export/
├── train/
│   ├── images/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   └── labels/
│       ├── img001.txt
│       ├── img002.txt
│       └── ...
├── valid/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
```

Each `.txt` label file contains one line per object:
```
class_id center_x center_y width height
```
All values are normalized to 0-1.

## Step 3: Import into Training Pipeline

### Option A: Import from Zip (Recommended)

```bash
cd hybrid-model

# Import directly from Roboflow export zip
python import_roboflow.py --zip path/to/roboflow_export.zip
```

### Option B: Import from Folder

If you already extracted the zip:

```bash
python import_roboflow.py --folder path/to/roboflow_export/
```

### Option C: Custom Validation Split

By default, 15% of data is used for validation. To change:

```bash
python import_roboflow.py --zip export.zip --val-split 0.2
```

### Option D: Also Copy Frames for LSTM Training

If you want the images available for LSTM feature extraction too:

```bash
python import_roboflow.py --zip export.zip --also-frames
```

## Step 4: Train Custom YOLO

After importing:

```bash
# Train YOLOv8 on your custom classes
python train_yolo_custom.py
```

This will:
1. Read annotations from `data/labels/annotations.json`
2. Create YOLO dataset in `data/yolo_dataset/`
3. Fine-tune YOLOv8s for 150 epochs
4. Save best weights to `models/yolov8_milking_custom.pt`

## Step 5: Use Trained Weights

Copy the custom YOLO weights to the inference service:

```bash
python -c "import shutil; shutil.copy('models/yolov8_milking_custom.pt', '../Monitoring_App/milking-monitor/apps/inference-service/models/')"
```

Then update the inference service to use the custom model.

## File Structure After Import

```
hybrid-model/
├── data/
│   ├── labels/
│   │   └── annotations.json      # Converted from Roboflow
│   ├── yolo_dataset/             # YOLO format dataset
│   │   ├── dataset.yaml
│   │   ├── images/
│   │   │   ├── train/
│   │   │   └── val/
│   │   └── labels/
│   │       ├── train/
│   │       └── val/
│   └── frames/                   # (optional) Images for LSTM training
├── import_roboflow.py            # Import script
├── train_yolo_custom.py          # Training script
└── models/
    └── yolov8_milking_custom.pt  # Trained weights
```

## Troubleshooting

### "Could not find images/ and labels/"
Make sure your Roboflow export is in YOLO format. The script expects:
```
export/
├── images/
│   └── *.jpg
└── labels/
    └── *.txt
```

### "No annotations found"
Check that your label files have the correct format:
```
class_id center_x center_y width height
```
All values must be normalized (0-1).

### Training Fails
- Ensure you have at least 10-20 images per class
- Check that images are valid (not corrupted)
- Verify class IDs are 0-5 (6 classes total)
