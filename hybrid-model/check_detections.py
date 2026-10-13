"""Check YOLO detection density across all frames."""
import numpy as np
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))
from detection.enhanced_yolo import EnhancedYOLODetector
from config import load_config
import cv2

config = load_config()
detector = EnhancedYOLODetector(config)

frames_dir = Path("data/frames")
total = 0
detected = 0
person_frames = 0

for task_dir in sorted(frames_dir.iterdir()):
    if not task_dir.is_dir():
        continue
    task_total = 0
    task_person = 0
    for img_path in sorted(task_dir.glob("*.jpg"))[:20]:  # sample 20 per task
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue
        task_total += 1
        total += 1
        result = detector.model(frame, conf=0.3, imgsz=640, verbose=False)
        has_person = False
        for r in result:
            if r.boxes is None:
                continue
            for box in r.boxes:
                if box.cls.item() == 0:
                    has_person = True
                    break
            if has_person:
                break
        if has_person:
            task_person += 1
            person_frames += 1
    print(f"{task_dir.name}: {task_person}/{task_total} frames with person")

print(f"\nTotal: {person_frames}/{total} frames with person ({person_frames/max(total,1)*100:.1f}%)")
