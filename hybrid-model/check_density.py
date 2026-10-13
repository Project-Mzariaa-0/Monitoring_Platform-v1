"""Check detection density with new threshold."""
import numpy as np
import cv2
from pathlib import Path
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
frames_dir = Path("data/frames")

for conf_thresh in [0.15, 0.10, 0.05]:
    total = 0
    person_frames = 0
    for task_dir in sorted(frames_dir.iterdir()):
        if not task_dir.is_dir():
            continue
        for img_path in sorted(task_dir.glob("*.jpg"))[:20]:
            frame = cv2.imread(str(img_path))
            if frame is None:
                continue
            total += 1
            results = model(frame, conf=conf_thresh, imgsz=640, verbose=False)
            for r in results:
                if r.boxes is not None:
                    for box in r.boxes:
                        if box.cls.item() == 0:
                            person_frames += 1
                            break
                    break
    print(f"conf={conf_thresh}: {person_frames}/{total} frames with person ({person_frames/max(total,1)*100:.1f}%)")
