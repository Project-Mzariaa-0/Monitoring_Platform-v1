# ML Spike — YOLOv8 Webcam Detection Experiment

## Objective

Validate whether a standard YOLOv8 model can detect relevant objects in a barn-like environment using a consumer webcam, and identify what custom training is needed for milking-specific detection.

## Setup

- **Camera**: Logitech C920 USB webcam (1080p)
- **Position**: Side angle, ~2m from subject, covering a single "cow position" proxy area
- **Model**: YOLOv8n (nano, COCO-pretrained, 80 classes)
- **Framework**: Ultralytics + OpenCV
- **Duration**: 300 frames captured over ~60 seconds
- **Environment**: Indoor room simulating barn conditions (artificial lighting, partial occlusion)

## Method

1. Captured 300 consecutive frames from the webcam
2. Ran `yolov8n.pt` inference on each frame
3. Logged all detected classes, confidence scores, and bounding boxes
4. Analyzed which COCO classes overlap with milking task detection signals

## Results

### Detection Summary

| Class | Detected | Avg Confidence | Frames Detected |
|-------|----------|---------------|-----------------|
| `person` | Yes | 0.87 | 280/300 |
| `bed` | Yes | 0.72 | 45/300 |
| `chair` | Yes | 0.65 | 12/300 |
| `bottle` | No | — | 0/300 |
| `cup` | No | — | 0/300 |

### Key Findings

1. **`person` detection works well** — High confidence, consistent across frames. This validates TASK-01, TASK-02, and TASK-06 signal detection (all require `person`).

2. **No milking-specific classes exist in COCO** — The 80 COCO classes include zero milking-related objects. The following required classes are entirely absent:
   - `spray_bottle` (TASK-01)
   - `stripping_cup` (TASK-02)
   - `teat_cups_attached` (TASK-03, TASK-04)
   - `teat_cups_detached` (TASK-05)
   - `dip_applicator` (TASK-06)

3. **`bottle` is close but insufficient** — COCO has a `bottle` class, but it detects beverage bottles, not spray bottles used for udder cleaning. The shape/context is different enough that transfer learning alone won't work.

4. **Background clutter** — `bed` and `chair` detections show the model tries to classify everything. In a real barn, expect similar false positives for hay bales, milking equipment, etc.

5. **Occlusion matters** — When a person stands close to the camera, bounding boxes for held objects are occluded. This confirms the spec limitation (LIM-02): side-angle cameras can verify task occurrence but not execution quality.

## What This Means

### Can we use COCO pretrained YOLOv8 as-is?

**Partially.** Only the `person` class is usable. For the 6-task detection system:

| Task | Signal | COCO Coverage | Status |
|------|--------|--------------|--------|
| TASK-01 | `person` + `spray_bottle` | `person` only | Needs custom `spray_bottle` class |
| TASK-02 | `person` + `stripping_cup` | `person` only | Needs custom `stripping_cup` class |
| TASK-03 | `teat_cups_attached` | None | Needs custom class |
| TASK-04 | `teat_cups_attached` | None | Needs custom class |
| TASK-05 | `teat_cups_detached` | None | Needs custom class |
| TASK-06 | `person` + `dip_applicator` | `person` only | Needs custom `dip_applicator` class |

### What's needed for production

1. **Custom YOLOv8 model** trained on domain-specific data with these classes:
   - `person` (can start from COCO pretrained)
   - `spray_bottle`
   - `stripping_cup`
   - `teat_cups_attached`
   - `teat_cups_detached`
   - `dip_applicator`
   - `udder` (optional, for ROI validation)

2. **Training data requirements**:
   - 500-1000 labeled images per class minimum
   - Multiple employees, lighting conditions, cow positions
   - Both attached and detached teat cup states
   - Video segments with start/end timestamps (not just bounding boxes)

3. **Labeling tool**: Use [Roboflow](https://roboflow.com/) or [CVAT](https://cvat.ai/) for bounding box annotation

4. **Training script** (to be created):
   ```python
   from ultralytics import YOLO

   model = YOLO("yolov8n.pt")  # Start from COCO pretrained
   results = model.train(
       data="barn_dataset.yaml",
       epochs=100,
       imgsz=640,
       batch=16,
       name="milking-v1",
   )
   ```

## Running the Spike Yourself

### Prerequisites

- Python 3.12+
- Webcam connected
- `pip install ultralytics opencv-python`

### Quick test

```python
from ultralytics import YOLO
import cv2

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)  # USB webcam

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, verbose=False)
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            name = model.names[cls]
            print(f"{name}: {conf:.2f}")

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
```

### Capture frames for analysis

```python
from ultralytics import YOLO
import cv2, json

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(0)
detections = []

for i in range(300):
    ret, frame = cap.read()
    if not ret:
        break
    results = model.predict(frame, verbose=False)
    for r in results:
        for box in r.boxes:
            detections.append({
                "frame": i,
                "class": model.names[int(box.cls[0])],
                "confidence": float(box.conf[0]),
            })

cap.release()
with open("detection_log.json", "w") as f:
    json.dump(detections, f, indent=2)
```

## Next Steps

1. **Collect training data** — Record video of actual milking sessions, extract frames, label with custom classes
2. **Train custom model** — Fine-tune YOLOv8n on labeled barn data
3. **Validate on real stream** — Test trained model against RTSP camera feed
4. **Tune state machine** — Adjust `thresholds.json` confidence values based on real model performance
5. **A/B test** — Compare custom model vs COCO baseline on same footage
