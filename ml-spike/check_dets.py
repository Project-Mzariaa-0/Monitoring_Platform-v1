import json

d = json.load(open("results/day_session_results.json"))
classes = {}
for f in d["detections"]:
    for det in f["detections"]:
        cls = det["class"]
        conf = det["confidence"]
        if cls not in classes:
            classes[cls] = {"count": 0, "conf": 0}
        classes[cls]["count"] += 1
        classes[cls]["conf"] += conf

for cls, info in sorted(classes.items(), key=lambda x: -x[1]["count"]):
    avg = info["conf"] / info["count"]
    print(f"{cls}: {info['count']} detections, avg conf: {avg:.3f}")
