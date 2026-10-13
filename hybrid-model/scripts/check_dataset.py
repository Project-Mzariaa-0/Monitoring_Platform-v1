#!/usr/bin/env python3
import json, os, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--annotations", default="hybrid-model/data/labels/annotations.json")
parser.add_argument("--yolo_labels", default="hybrid-model/data/yolo_dataset/labels")
parser.add_argument("--classes", type=int, default=6)
args = parser.parse_args()

with open(args.annotations, "r", encoding="utf8") as f:
    ann = json.load(f)

if isinstance(ann, dict) and "images" in ann:
    images = ann["images"]
else:
    images = ann

print(f"Annotations entries: {len(images)}")

missing_txt = []
out_of_range = []
sample_problems = []
for img_path, boxes_wrapper in images.items():
    base = os.path.splitext(os.path.basename(img_path))[0]
    txt_path = os.path.join(args.yolo_labels, base + ".txt")
    if not os.path.exists(txt_path):
        missing_txt.append(txt_path)
    boxes = boxes_wrapper.get("boxes") if isinstance(boxes_wrapper, dict) and "boxes" in boxes_wrapper else boxes_wrapper
    if isinstance(boxes, list):
        for b in boxes:
            cls = b.get("class", b.get("class_id"))
            try:
                ci = int(cls)
            except Exception:
                sample_problems.append((img_path, f"invalid class {cls}"))
                continue
            if ci < 0 or ci > args.classes:
                out_of_range.append((img_path, ci))
    else:
        sample_problems.append((img_path, "boxes not list"))

print(f"Missing YOLO txt files: {len(missing_txt)}")
if missing_txt:
    print("Sample missing:", missing_txt[:10])
print(f"Out-of-range class count: {len(out_of_range)}")
if out_of_range:
    print("Sample out-of-range:", out_of_range[:10])
print("Sample other problems:", sample_problems[:10])
