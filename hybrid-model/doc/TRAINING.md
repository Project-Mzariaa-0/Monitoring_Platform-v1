# Training Guide

## Overview

There are two training pipelines:

1. **Custom YOLO Training** — Fine-tune YOLOv8 on milking objects
2. **LSTM Training** — Train temporal model on frame sequences

## Custom YOLO Training

### Prerequisites
- Annotated images in `data/labels/annotations.json` (from Roboflow or `label_tool.py`)

### Train

```bash
cd hybrid-model
python train_yolo_custom.py
```

### What It Does
1. Reads `data/labels/annotations.json`
2. Converts to YOLO format in `data/yolo_dataset/`
3. Splits 85/15 train/val
4. Fine-tunes YOLOv8s for 150 epochs
5. Saves best weights to `models/yolov8_milking_custom.pt`

### Output
```
models/
├── milking_custom/
│   └── weights/
│       └── best.pt
└── yolov8_milking_custom.pt    # Final weights
```

## LSTM Training

### Prerequisites
- Video clips in `data/raw/` organized by task folder
- Extracted frames in `data/frames/`

### Full Pipeline

```bash
# Extract frames + train
python run_pipeline.py --epochs 200
```

### Skip Frame Extraction (if frames already exist)

```bash
python run_pipeline.py --skip-frames --seq-length 30 --epochs 200
```

### What It Does
1. Extracts frames from video clips at 5 FPS
2. Runs multimodal feature extraction (YOLOv8-Pose + YOLOv8n)
3. Creates sequences of 30 frames
4. Augments data (8x)
5. Trains LSTM model
6. Saves best weights to `models/checkpoints/best_model.pt`

### Output
```
models/checkpoints/
└── best_model.pt    # 9.2 MB, 73.53% val accuracy
```

## Copy Weights to Inference Service

### Custom YOLO
```bash
python -c "import shutil; shutil.copy('models/yolov8_milking_custom.pt', '../Monitoring_App/milking-monitor/apps/inference-service/models/')"
```

### LSTM Model
```bash
python -c "import shutil; shutil.copy('models/checkpoints/best_model.pt', '../Monitoring_App/milking-monitor/apps/inference-service/models/checkpoints/best_model.pt')"
```

## Training Results

| Model | Val Accuracy | Epochs | Parameters |
|-------|-------------|--------|------------|
| LSTM (current) | 73.53% | 62 (early stop) | 2.3M |
| LSTM (previous) | 70.59% | 33 (early stop) | 148K |
| Custom YOLO | mAP50=21.7% | 150 | — |

## Tips

- **More data = better accuracy** — aim for 500+ sequences
- **Balance your classes** — equal clips per task
- **Use GPU if available** — training is 10x faster
- **Monitor overfitting** — if train acc >> val acc, reduce epochs
