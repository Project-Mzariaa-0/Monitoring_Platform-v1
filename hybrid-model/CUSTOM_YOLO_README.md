# Custom YOLO Training for Milking Objects

## Classes to Label

| ID | Class | What to look for |
|----|-------|------------------|
| 1 | person | Worker in the aisle |
| 2 | pipe_sprayer | Water pipe/sprayer held by person (TASK-01) |
| 3 | stripping_cup | Handheld stripping device (TASK-02) |
| 4 | teat_cup_on | Milking cups attached to cow udder (TASK-03/04) |
| 5 | teat_cup_off | Cups dangling in holder after detachment (TASK-05) |
| 6 | dip_applicator | Cup/applicator for post-dip (TASK-06) |

## Workflow

### Step 1: Label Images

```bash
cd hybrid-model
python label_tool.py
```

1. Click "Load Folder" → select `data/frames/task_01_precleaning`
2. Select class (1-6) using radio buttons
3. Click and drag to draw bounding boxes around objects
4. Press 'n' for next image, 'p' for previous
5. Press 's' to save annotations
6. Repeat for all 6 task folders

### Step 2: Train YOLO

```bash
python train_yolo_custom.py --prepare
python train_yolo_custom.py
```

This will:
- Split data 85/15 train/val
- Fine-tune YOLOv8n for 50 epochs
- Save weights to `models/yolov8_milking_custom.pt`

### Step 3: Use in Inference Service

Copy the trained weights:
```bash
cp models/yolov8_milking_custom.pt ../Monitoring_App/milking-monitor/apps/inference-service/weights/
```

Update the inference service to use custom weights.

## Tips

- Label at least 50-100 images per class for good results
- Label ALL visible instances, not just obvious ones
- Include different angles, lighting conditions, and cow positions
- The more consistent your labels, the better the model will learn
