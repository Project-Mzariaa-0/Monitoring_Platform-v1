import json
from pathlib import Path

d = json.loads(Path("results/webcam_0_raw_detections.json").read_text())
print(f"Clip: {d['clip_name']}")
print(f"Frames captured: {len(d['rois'][0]['frames'])}")

for r in d["rois"]:
    total = sum(len(f["detections"]) for f in r["frames"])
    nonzero = sum(1 for f in r["frames"] if f["detections"])
    print(f"\nROI '{r['roi']}':")
    print(f"  Frames with detections: {nonzero}/{len(r['frames'])}")
    print(f"  Total detections: {total}")

    classes = {}
    for f in r["frames"]:
        for det in f["detections"]:
            classes[det["class"]] = classes.get(det["class"], 0) + 1
    if classes:
        print(f"  Class breakdown:")
        for cls, count in sorted(classes.items(), key=lambda x: -x[1]):
            print(f"    {cls}: {count}")
    else:
        print("  No objects detected")

    avg_conf = 0
    conf_count = 0
    for f in r["frames"]:
        for det in f["detections"]:
            avg_conf += det["confidence"]
            conf_count += 1
    if conf_count > 0:
        print(f"  Average confidence: {avg_conf / conf_count:.3f}")
