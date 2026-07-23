# Data Collection Guide

## Video Requirements

- **Resolution**: 1920x1080 or higher
- **FPS**: 12-30 FPS (extracted at 5 FPS)
- **Format**: MP4, MOV, or AVI
- **Duration**: 5-30 seconds per clip

## Task Descriptions

### TASK-01: Pre-cleaning
- Person holds water pipe/sprayer
- Sprays water on cow udder
- Arms raised, working posture
- Duration: 5-15 seconds

### TASK-02: Stripping
- Person manually strips foremilk
- Hand on udder, milking motion
- Duration: 5-10 seconds

### TASK-03: Machine Attachment
- Person attaches milking cups
- Crouching at cow side
- Cups go from holder to udder
- Duration: 10-20 seconds

### TASK-04: Milking
- Cups attached to udder
- Person may be walking or standing
- Machine milking in progress
- Duration: 30-120 seconds

### TASK-05: Detachment
- Cups detach from udder
- Cups dangling in holder
- Person may be walking away
- Duration: 5-15 seconds

### TASK-06: Post-dip
- Person walks to dip station
- Fills dip cup
- Applies iodine to udder
- Duration: 10-20 seconds

## Collection Tips

### Camera Angle
- Mount camera high on wall, looking down at 30-45 degrees
- Capture both cow rows and center aisle
- Ensure dip station is visible (bottom-right corner)

### Lighting
- Consistent lighting preferred
- Avoid extreme shadows
- Night vision OK if clear

### Person Visibility
- Ensure person is visible in most frames
- Multiple persons OK (up to 2)
- Different workers help generalization

### Cow Positions
- Different cows in different clips
- Various udder positions
- Different stages of milking

## Dataset Organization

```
data/raw/
├── task_01_precleaning/
│   ├── clip1.MOV
│   ├── clip2.MOV
│   └── clip3.MOV
├── task_02_stripping/
│   ├── clip1.MOV
│   └── clip2.MOV
├── task_03_attachment/
│   ├── clip1.MOV
│   └── clip2.MOV
├── task_04_milking/
│   └── clip1.MOV
├── task_05_detachment/
│   └── clip1.MOV
└── task_06_postdip/
    ├── clip1.MOV
    └── clip2.MOV
```

## Frame Extraction

```bash
cd hybrid-model

# Extract frames from all clips
python add_clip.py

# Or extract from specific clip
python add_clip.py --input data/raw/task_01_precleaning/clip1.MOV
```

## Minimum Dataset Size

| Task | Min Clips | Min Frames | Target Sequences |
|------|-----------|------------|------------------|
| TASK-01 | 10 | 500 | 15+ |
| TASK-02 | 10 | 500 | 15+ |
| TASK-03 | 10 | 500 | 15+ |
| TASK-04 | 10 | 500 | 15+ |
| TASK-05 | 10 | 500 | 15+ |
| TASK-06 | 10 | 500 | 15+ |
| **Total** | **60** | **3000** | **90+** |
