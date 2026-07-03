# ML Feasibility Spike

This spike answers one question: can a fixed side camera plus a YOLOv8-based detector and a simple rule-based state machine detect the six milking tasks with usable confidence at the current camera angle?

## Scope

- Input: short sample clips from the actual camera view
- Output: raw detections, candidate task events, and a small evaluation summary
- Non-goals: app code, database persistence, authentication, production hardening, final model thresholds

## Expected folder layout

- `data/raw_clips/` sample footage clips
- `data/ground_truth/` human-labeled task timing files
- `data/rois.json` ROI definitions for the two monitored cow positions
- `models/` local YOLOv8 weights or pretrained checkpoints
- `results/` generated detections, task events, evaluations, and summary notes
- `src/detect_objects.py` frame-by-frame detection runner
- `src/state_machine.py` rule-based task inference
- `src/evaluate.py` comparison against human labels

## How to use

1. Put sample clips in `data/raw_clips/`.
2. Define the two ROIs in `data/rois.json`.
3. Add human labels in `data/ground_truth/`.
4. Run detection to generate raw per-frame detections.
5. Run the state machine to convert detections into task events.
6. Run evaluation to compare predicted events against labels.

## Goal of the spike

The spike is successful if it shows a usable signal for the six tasks and clearly identifies where occlusion makes the camera angle unreliable.