# Hybrid YOLO + LSTM Milking Detection Model

Real-time milking task detection using multimodal feature extraction (YOLOv8-Pose + YOLOv8n) and LSTM for temporal action recognition.

## Architecture

```
Frame (1248x576)
    │
    ├────────────────────────────┐
    ▼                            ▼
┌──────────────────┐    ┌──────────────────┐
│  YOLOv8-Pose     │    │  YOLOv8n         │
│  (yolov8n-pose)  │    │  (yolov8n)       │
│  17 keypoints    │    │  80 COCO classes │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         ▼                       ▼
┌──────────────────┐    ┌──────────────────┐
│  Pose Features   │    │  Object Features │
│  (512 dims)      │    │  (128 dims)      │
│  · person detect │    │  · class counts  │
│  · arm pose      │    │  · confidence    │
│  · row position  │    │  · bbox stats    │
│  · keypoints     │    │  · spatial grid  │
│  · motion        │    │  · temporal      │
│  · action        │    │  · proximity     │
│  · visual        │    │                  │
└────────┬─────────┘    └────────┬─────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
            ┌─────────────────┐
            │  Concatenate    │
            │  (640 dims)     │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  LSTM Model     │
            │  (30 frames)    │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  Task Classes   │
            │  6 milking      │
            │  tasks          │
            └─────────────────┘
```

## Documentation

See the [`doc/`](doc/) folder for detailed guides:

| Guide | Description |
|-------|-------------|
| [ROBOFLOW_IMPORT.md](doc/ROBOFLOW_IMPORT.md) | Import annotated data from Roboflow |
| [TRAINING.md](doc/TRAINING.md) | How to train the model |
| [ARCHITECTURE.md](doc/ARCHITECTURE.md) | Model architecture details |
| [DATA_COLLECTION.md](doc/DATA_COLLECTION.md) | How to collect training data |

## Quick Start

```bash
cd hybrid-model
pip install -r requirements.txt

# Extract frames from video clips
python add_clip.py

# Train (full pipeline)
python run_pipeline.py --skip-frames --seq-length 30 --epochs 200

# Copy weights to inference service
python -c "import shutil; shutil.copy('models/checkpoints/best_model.pt', '../Monitoring_App/milking-monitor/apps/inference-service/models/checkpoints/best_model.pt')"
```

## Model Details

### Feature Extraction (640 dims per frame)

**Pose Features (512 dims)** — YOLOv8-Pose with 17 COCO keypoints:

| Section | Dims | Description |
|---------|------|-------------|
| Person detection | 0-49 | Count, positions, spatial info |
| Arm pose | 50-99 | Arm raise detection, arm angles, working posture |
| Row position | 100-149 | Left/right cow row, dip station, movement history |
| Keypoint positions | 150-199 | All 17 normalized keypoints, arm angles |
| Motion | 200-249 | Displacement, speed, direction between frames |
| Temporal stats | 250-299 | Running averages, std dev over 30 frames |
| Action features | 300-349 | Walking vs working, bending, dip station proximity |
| Visual features | 350-511 | Brightness, contrast, person region size |

**Object Features (128 dims)** — YOLOv8n on 80 COCO classes:

| Section | Dims | Description |
|---------|------|-------------|
| Per-class detection | 0-48 | Count, confidence, binary, bbox center/size |
| Aggregate stats | 49-58 | Total objects, person/non-person ratio |
| Spatial grid | 59-70 | 3x3 grid distribution |
| Temporal stats | 71-82 | Running mean, std, delta over 30 frames |
| Object-person proximity | 86-127 | Distance to nearest object, nearby count |

### Arm Detection (High Camera Angle)

Camera looks down from wall. "Arm extended" means wrist below shoulder in image coords (forward toward cow):

```python
forward = wrist.y > shoulder.y + threshold  # arm extended forward
away = abs(wrist.x - body_center.x) > person_height * 0.15  # arm away from body
arm_raised = forward and away
```

### Row Detection

| Position | x_ratio | Description |
|----------|---------|-------------|
| Left row | < 0.4 | Cow row left of center |
| Center | 0.4 - 0.6 | Aisle between rows |
| Right row | > 0.6 | Cow row right of center |
| Dip station | > 0.75, y > 0.7 | Bottom-right corner |

### LSTM Temporal Model

```
input(640) → Linear(64) → ReLU → Dropout(0.3)
    → LSTM(64, 256, 2 layers, bidirectional)
    → Attention(512 → 32 → 1) → weighted sum
    → Linear(512 → 32) → ReLU → Dropout(0.3) → Linear(32 → 6)
```

| Parameter | Value |
|-----------|-------|
| Input size | 640 |
| Hidden size | 256 |
| Layers | 2 (bidirectional) |
| Dropout | 0.3 |
| Attention | Self-attention pooling |
| Parameters | 2,310,503 |
| Model size | 9.2 MB |

### Supported Tasks

| Task | Name | Description | Visual Signal |
|------|------|-------------|---------------|
| TASK-01 | Pre-cleaning | Spray water on udder | Person holds pipe, arms raised |
| TASK-02 | Stripping | Strip foremilk by hand | Person hand on udder |
| TASK-03 | Machine attachment | Attach milking cups | Person crouching at cow |
| TASK-04 | Milking | Cups attached, milking | Cups on udder, person walking |
| TASK-05 | Detachment | Remove milking cups | Cups dangling in holder |
| TASK-06 | Post-dip | Apply iodine dip | Person at dip station, dips cup |

## Training

### Dataset

- **Frames**: 4,775 extracted across 6 task folders
- **Sequences**: 161 (30 frames each @ 5 FPS = 6 seconds)
- **Augmentation**: 8x (horizontal flip, rotation ±15°, brightness/contrast ±20%)
- **Splits**: 127 train / 34 val (80/20)

### Results

| Metric | Value |
|--------|-------|
| Best val accuracy | **73.53%** |
| Best epoch | 37 |
| Early stopped | Epoch 62 (patience 25) |
| Train accuracy | 90.46% |
| Model size | 9.2 MB |

### 5-Fold Cross-Validation (previous run)

| Fold | Val Accuracy |
|------|-------------|
| 1 | 65.62% |
| 2 | 52.94% |
| 3 | 58.82% |
| 4 | 55.88% |
| 5 | 61.76% |
| **Mean** | **58.67% ± 6.53%** |

## Project Structure

```
hybrid-model/
├── doc/                                     # Documentation
│   ├── README.md                            # Documentation index
│   ├── ROBOFLOW_IMPORT.md                   # Roboflow import guide
│   ├── TRAINING.md                          # Training guide
│   ├── ARCHITECTURE.md                      # Architecture details
│   └── DATA_COLLECTION.md                   # Data collection guide
├── src/
│   ├── config.py                          # Model configuration
│   ├── detection/
│   │   ├── multimodal_feature_extractor.py  # Combined pose + object features
│   │   ├── pose_feature_extractor.py      # YOLOv8-Pose (512 dims)
│   │   └── object_feature_extractor.py    # YOLOv8n (128 dims)
│   ├── temporal/
│   │   └── lstm_model.py                  # LSTM with attention
│   └── training/
│       ├── augmentation.py                # 8x data augmentation
│       └── train.py                       # Training loop
├── configs/
│   └── default.yaml                       # All hyperparameters
├── models/
│   └── checkpoints/
│       └── best_model.pt                  # Trained weights (9.2 MB)
├── data/
│   ├── frames/                            # 4,775 extracted frames
│   └── raw/                               # Original video clips
├── run_pipeline.py                        # Full training pipeline
├── train_yolo_custom.py                   # Custom YOLO training
├── import_roboflow.py                     # Roboflow import script
├── semi_auto_labeler.py                   # Annotation tool
├── add_clip.py                            # Frame extraction
└── requirements.txt
```

## Inference Service Integration

```python
# inference-service/src/detection/hybrid_detector.py
from detection.multimodal_feature_extractor import MultimodalFeatureExtractor

extractor = MultimodalFeatureExtractor(config)  # runs YOLOv8-Pose + YOLOv8n
features = extractor.extract_features(frame)    # 640-dim vector
```

The inference service:
- Runs both YOLO models per frame (~0.24s)
- Buffers 30 frames, then runs LSTM inference
- Uses temporal smoothing (3/5 consecutive predictions)
- Detects task switches with 5s minimum per task
- Publishes task events to the web app via HTTP
