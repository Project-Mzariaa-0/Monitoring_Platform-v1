# Hybrid YOLO + LSTM Milking Detection Model

Real-time milking task detection using YOLO for object detection and LSTM for temporal action recognition.

## Architecture

```
Frame Sequence (30 frames @ 5 FPS = 6 seconds)
    │
    ▼
┌─────────────────────────────────────┐
│         YOLOv8n (Per Frame)         │
│  - Detects: person, objects         │
│  - Extracts: bounding boxes         │
│  - Speed: 20ms/frame                │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│      Feature Aggregator             │
│  - Combines 30 frames of YOLO data  │
│  - Adds motion vectors              │
│  - Normalizes positions             │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│         LSTM (Temporal)             │
│  - Analyzes sequence pattern        │
│  - Classifies action                │
│  - Predicts completion              │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│         State Machine               │
│  - Maps actions to tasks            │
│  - Tracks progress                  │
└─────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd hybrid-model
pip install -r requirements.txt
```

### 2. Prepare Dataset

```bash
# Organize your video clips
python src/data/organize_dataset.py --input /path/to/videos --output data/raw

# Extract frames and annotations
python src/data/extract_frames.py --input data/raw --output data/processed
```

### 3. Train Model

```bash
# Train LSTM model
python src/train.py --epochs 100 --batch-size 32

# Evaluate
python src/evaluate.py --model models/best.pt
```

### 4. Run Inference

```bash
# Real-time detection
python src/inference.py --source rtsp://camera-ip/stream

# Test on video file
python src/inference.py --source test_video.mp4
```

## Project Structure

```
hybrid-model/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── yolo_detector.py   # YOLO feature extractor
│   │   └── feature_extractor.py
│   ├── temporal/
│   │   ├── __init__.py
│   │   ├── lstm_model.py      # LSTM model
│   │   └── sequence_dataset.py
│   ├── training/
│   │   ├── __init__.py
│   │   ├── train.py           # Training loop
│   │   └── evaluate.py        # Evaluation metrics
│   ├── inference/
│   │   ├── __init__.py
│   │   └── hybrid_detector.py # Combined detector
│   ├── data/
│   │   ├── __init__.py
│   │   ├── organize_dataset.py
│   │   └── extract_frames.py
│   └── utils/
│       ├── __init__.py
│       ├── visualization.py
│       └── metrics.py
├── configs/
│   └── default.yaml           # Default config
├── data/
│   ├── raw/                   # Raw video clips
│   ├── processed/             # Extracted frames
│   └── splits/                # Train/val/test splits
├── models/                    # Saved models
├── notebooks/                 # Jupyter notebooks
├── tests/                     # Unit tests
├── requirements.txt
├── setup.py
└── README.md
```

## Model Details

### YOLO Feature Extractor
- **Model**: YOLOv8n (COCO pretrained)
- **Output**: 256-dim feature vector per frame
- **Speed**: ~20ms/frame on CPU

### LSTM Temporal Model
- **Input**: 30-frame sequence (6 seconds)
- **Hidden size**: 256
- **Layers**: 2 (bidirectional)
- **Output**: 6 task probabilities

### Supported Tasks
| Task | Description |
|------|-------------|
| TASK-01 | Pre-cleaning |
| TASK-02 | Stripping |
| TASK-03 | Machine attachment |
| TASK-04 | Milking (active) |
| TASK-05 | Detachment |
| TASK-06 | Post-dip |

## Dataset Requirements

- **Video clips**: 5-10 seconds each
- **Annotations**: Start/end times for each task
- **Quantity**: ~50 clips per task (300 total minimum)
- **Format**: MP4, 1920x1080 or higher

## Performance

| Metric | Target |
|--------|--------|
| FPS | 4+ |
| Accuracy | >85% |
| Latency | <500ms |
