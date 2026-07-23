# Architecture

## Multimodal Feature Extraction

Each frame is processed by two YOLO models in parallel:

```
Frame (1248x576)
    │
    ├────────────────────┐
    ▼                    ▼
┌──────────────┐  ┌──────────────┐
│ YOLOv8-Pose  │  │ YOLOv8n      │
│ (keypoints)  │  │ (objects)    │
└──────┬───────┘  └──────┬───────┘
       │                 │
       ▼                 ▼
  512 dims           128 dims
       │                 │
       └────────┬────────┘
                ▼
         640 dims/frame
```

### Pose Features (512 dims)

| Section | Dims | Description |
|---------|------|-------------|
| Person detection | 0-49 | Count, positions, spatial info |
| Arm pose | 50-99 | Arm raise detection, angles |
| Row position | 100-149 | Left/right row, dip station |
| Keypoints | 150-199 | All 17 normalized keypoints |
| Motion | 200-249 | Displacement between frames |
| Temporal stats | 250-299 | Running averages over 30 frames |
| Action | 300-349 | Walking vs working, bending |
| Visual | 350-511 | Brightness, contrast, person region |

### Object Features (128 dims)

| Section | Dims | Description |
|---------|------|-------------|
| Per-class detection | 0-48 | Count, confidence, bbox stats |
| Aggregate | 49-58 | Total objects, person ratio |
| Spatial grid | 59-70 | 3x3 grid distribution |
| Temporal | 71-82 | Running stats over 30 frames |
| Proximity | 86-127 | Object-person distances |

## LSTM Model

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

## Task Detection

| Task | Name | Visual Signal |
|------|------|---------------|
| TASK-01 | Pre-cleaning | Person holds pipe, arms raised |
| TASK-02 | Stripping | Person hand on udder |
| TASK-03 | Attachment | Person crouching at cow |
| TASK-04 | Milking | Cups on udder, person walking |
| TASK-05 | Detachment | Cups dangling in holder |
| TASK-06 | Post-dip | Person at dip station |

## Inference Pipeline

1. Frame arrives from camera/video
2. MultimodalFeatureExtractor runs YOLOv8-Pose + YOLOv8n (~0.24s)
3. 640-dim feature vector appended to buffer
4. When buffer has 30 frames, LSTM runs inference
5. Temporal smoothing (3/5 consecutive predictions)
6. Task switch detected after 5s minimum
7. Task completion detected at 10% of session frames
8. Events published to web app via HTTP
