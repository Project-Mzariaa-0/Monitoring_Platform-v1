# Hybrid YOLO + LSTM — Training Progress

> Generated: 2026-07-13

---

## 1. Project Overview

**Goal:** Automatically detect which of the 6 milking tasks is being performed in a video clip.

**Approach:** YOLO (object detection) → frame-level features (512-dim) → LSTM (temporal classification)

**Tasks:**

| ID | Name | Description |
|----|------|-------------|
| TASK-01 | Pre-cleaning | Person lifts pipe and shoots water |
| TASK-02 | Stripping | Manual stripping of teats |
| TASK-03 | Attachment | Attaching milking machine cups |
| TASK-04 | Milking | Machine milking in progress |
| TASK-05 | Detachment | Removing milking cups |
| TASK-06 | Post-dip | Person fills cup at station, applies dip |

---

## 2. Dataset

### Video Clips

| Task | Clips | Source |
|------|-------|--------|
| TASK-01 Pre-cleaning | 3 | `task_01_precleaning/*.mov` |
| TASK-02 Stripping | 3 | `task_02_stripping/*.mov` |
| TASK-03 Attachment | 3 | `task_03_attachment/*.mov` |
| TASK-04 Milking | 1 | `task_04_milking/*.mov` |
| TASK-05 Detachment | 0 | **No clips available** |
| TASK-06 Post-dip | 3 | `task_06_postdip/*.mov` |

### Extracted Frames (at 5 FPS)

| Task | Frames | Feature Dim |
|------|--------|-------------|
| TASK-01 Pre-cleaning | 420 | 512 |
| TASK-02 Stripping | 420 | 512 |
| TASK-03 Attachment | 420 | 512 |
| TASK-04 Milking | 186 | 512 |
| TASK-06 Post-dip | 1,367 | 512 |
| **Total** | **2,813** | — |

### Training Sequences (30 frames each, 50% overlap)

| Task | Sequences | Train | Val |
|------|-----------|-------|-----|
| TASK-01 | 27 | 22 | 5 |
| TASK-02 | 27 | 22 | 5 |
| TASK-03 | 27 | 22 | 5 |
| TASK-04 | 11 | 9 | 2 |
| TASK-06 | 90 | 72 | 18 |
| **Total** | **182** | **143** | **39** |

---

## 3. Feature Vector (512 dims)

The 512-dim feature vector per frame is composed of:

### YOLO Person Detection (dims 0–349)

| Range | Feature | Dims |
|-------|---------|------|
| 0–49 | Person bounding boxes (up to 2 persons × 25 dims) | 50 |
| 50–99 | Person center positions (up to 2 persons × 25 dims) | 50 |
| 100–149 | Person confidence scores | 50 |
| 150–199 | Arm raised detection | 50 |
| 200–249 | Near station detection | 50 |
| 250–299 | Holding object detection | 50 |
| 300–349 | Person count + interaction features | 50 |

### Frame-Level Visual Features (dims 350–511)

| Range | Feature | Dims |
|-------|---------|------|
| 350–353 | Brightness statistics (mean, std, min, max) | 4 |
| 354–359 | HSV statistics (H/S/V mean + std) | 6 |
| 360–383 | BGR color histograms (8 bins × 3 channels) | 24 |
| 384–385 | Edge density (Canny) + Laplacian variance | 2 |
| 386–390 | Region brightness (top, bottom, left, right quarters) | 5 |
| 391–392 | Dark region detection ratio | 2 |
| 393–511 | Reserved / padding | 119 |

**Note:** Currently only ~53/512 features are non-zero per frame (mostly zeros in person detection range since YOLO only detects "person", not task-specific objects).

---

## 4. Model Architecture

```
Input: (batch, 30, 512)  — 30 frames × 512 features
    ↓
Feature Extractor: Linear(512→128) + ReLU + Dropout → Linear(128→128) + ReLU + Dropout
    ↓
LSTM: input=128, hidden=256, layers=2, bidirectional=True
    ↓
Attention: Linear(512→64) + Tanh → Linear(64→1) + Softmax
    ↓
Context: attention-weighted sum over time steps
    ↓
Classifier: Linear(512→128) + ReLU + Dropout → Linear(128→64) + ReLU + Dropout → Linear(64→5)
    ↓
Output: (batch, 5) logits  — 5 classes (no TASK-05)
```

**Total Parameters:** 2,556,871

---

## 5. Training History

### Run 1: Baseline (512-dim features, 15 epochs)

| Epoch | Train Loss | Train Acc | Val Loss | Val Acc | Note |
|-------|------------|-----------|----------|---------|------|
| 1 | 1.774 | 21.0% | 1.745 | 46.2% | — |
| 2 | 1.631 | 50.3% | 1.602 | 46.2% | — |
| 3 | 1.565 | 50.3% | 1.488 | 46.2% | — |
| 4 | 1.397 | 50.3% | 1.417 | 46.2% | — |
| 5 | 1.244 | 50.3% | 1.077 | 46.2% | — |
| 6 | 0.952 | 51.0% | 0.987 | **61.5%** | Best |
| 7 | 0.906 | 63.6% | 0.966 | 61.5% | — |
| 8 | 0.893 | 64.3% | 0.945 | 61.5% | — |
| 9 | 0.814 | 64.3% | 0.921 | 61.5% | — |
| 10 | 0.793 | 66.4% | 0.906 | 61.5% | — |
| 11 | 0.779 | 62.2% | 0.898 | 61.5% | — |
| 12 | 0.816 | 62.2% | 0.897 | 61.5% | — |
| 13 | 0.776 | 61.5% | 0.894 | 61.5% | — |
| 14 | 0.732 | 65.0% | 0.892 | 61.5% | — |
| 15 | 0.745 | 67.1% | 0.891 | 61.5% | — |

**Best Val Accuracy: 61.5%** (Epoch 6)

### Accuracy Curve (ASCII)

```
100% |
 90% |
 80% |
 70% |                                                              ····
 60% |                              ··································
 50% |          ····················
 40% |·········
 30% |
 20% |·
 10% |
  0% |____________________________________________________________
     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15  Epoch
     
     ——— Train Acc    ···· Val Acc
```

### Loss Curve (ASCII)

```
 2.0 |
 1.8 |·
 1.6 |  ·  ·
 1.4 |       ·
 1.2 |        ·
 1.0 |         ·  ·
 0.8 |              ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·
 0.6 |
 0.4 |
 0.2 |
 0.0 |____________________________________________________________
     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15  Epoch
     
     ——— Train Loss    ···· Val Loss
```

---

## 6. Results Summary

| Metric | Value |
|--------|-------|
| Best Validation Accuracy | **61.5%** |
| Final Training Accuracy | 67.1% |
| Final Validation Accuracy | 61.5% |
| Overfitting Gap | 5.6% (train - val) |
| Early Stopping | No (completed 15 epochs) |
| Model Size | 10.2 MB |

### Per-Class Breakdown (Estimated)

The model tends to over-predict TASK-06 (Post-dip) because it has the most training data (90/182 sequences = 49.5%). With 5 classes, random chance is 20%, so 61.5% is a meaningful improvement.

---

## 7. Known Issues

### Data Imbalance
- TASK-06 dominates with 90 sequences (49.5% of dataset)
- TASK-04 has only 11 sequences (6.0%)
- TASK-05 has 0 sequences (0%) — no clips available

### Feature Quality
- Only ~53/512 features are non-zero per frame
- YOLO detects "person" but not task-specific objects (pipe, cups, dip station)
- Fixed camera angle means visual features are very similar across tasks
- Person not detected in many middle frames (occluded by cow)

### Model Limitations
- Validation accuracy plateaued at 61.5% after epoch 6
- No further improvement in last 9 epochs
- Model may be learning to predict TASK-06 majority class

---

## 8. Next Steps

### Short-term (Improve Accuracy)
1. **Collect TASK-05 clips** — need detachment videos
2. **Collect more TASK-04 clips** — only 1 clip available
3. **Use `imgsz=1280` in pipeline** — `run_pipeline.py` step2 still uses 640×640 resize
4. **Balance dataset** — use class weights or oversampling

### Medium-term (Better Features)
5. **Fine-tune YOLO on custom objects** — train on pipe, cups, dip station
6. **Crop frames around detected persons** — focus on relevant regions
7. **Add optical flow features** — capture motion between frames
8. **Use raw frame patches** — CNN on cropped person regions

### Long-term (Production)
9. **Train on GPU** — current training on CPU
10. **Hyperparameter search** — hidden_size, num_layers, dropout, lr
11. **Deploy model** — export to ONNX for inference service
12. **A/B test** — compare with rule-based approach

---

## 9. File Structure

```
hybrid-model/
├── models/
│   ├── checkpoints/
│   │   ├── best_model.pt        # Best validation accuracy (61.5%)
│   │   └── final_model.pt       # Final trained model
│   └── training_history.json    # Loss/accuracy curves
├── data/
│   ├── raw/                     # Video clips (9 files)
│   ├── features_v2/             # Extracted 512-dim features (2,813 frames)
│   ├── processed_v2/            # Training sequences (182 total)
│   └── splits_v2/               # Train/val split indices
├── src/
│   ├── detection/
│   │   └── enhanced_yolo.py     # YOLO feature extractor (512-dim)
│   ├── temporal/
│   │   ├── lstm_model.py        # LSTM classifier (2.5M params)
│   │   └── preextracted_dataset.py
│   └── config.py                # Configuration
├── configs/
│   └── default.yaml             # Full config
├── run_pipeline.py              # Full pipeline script
├── test_model.py                # Inference on video/images
└── TRAINING_PROGRESS.md         # This file
```

---

## 10. How to Reproduce

```bash
# Step 1: Extract frames (skip if already done)
python run_pipeline.py --skip-frames --skip-features --epochs 15

# Step 2: Run full pipeline (if starting fresh)
python run_pipeline.py --epochs 15

# Step 3: Test inference
python test_model.py --video data/raw/task_01_precleaning/video.MOV
```

---

*Last updated: 2026-07-13*
