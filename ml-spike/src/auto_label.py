"""Auto-label frames using YOLO pretrained detections + CLIP for milking classes.

This uses what already works (YOLO for person/bottle) and CLIP for zero-shot
similarity matching on the remaining classes. No fragile dependencies.

Install: pip install ultralytics opencv-python Pillow clip-python
"""

from __future__ import annotations

import argparse
import cv2
import numpy as np
from pathlib import Path


CLASS_PROMPTS = {
    "person": ["a person working", "a worker", "someone standing"],
    "spray_bottle": ["a spray bottle", "a cleaning spray", "a hand spray"],
    "stripping_cup": ["a stripping cup for milking", "a small cup for stripping", "hand stripping tool"],
    "teat_cups_attached": ["milking machine attached to cow udder", "teat cups on cow", "milking cluster attached"],
    "teat_cups_detached": ["milking machine detached from cow", "teat cups removed", "milking cluster hanging loose"],
    "dip_applicator": ["a dip cup for udder", "an applicator for disinfectant", "udder dip tool"],
}

CLASS_TO_ID = {
    "person": 0,
    "spray_bottle": 1,
    "stripping_cup": 2,
    "teat_cups_attached": 3,
    "teat_cups_detached": 4,
    "dip_applicator": 5,
}


def detect_with_yolo(frame, model):
    results = model.predict(frame, verbose=False)
    detections = []
    for r in results:
        for box in r.boxes:
            cls_name = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            xyxy = box.xyxy[0].tolist()
            detections.append({
                "class": cls_name,
                "confidence": conf,
                "bbox": xyxy,
            })
    return detections


def compute_clip_similarity(image_path: str, text_prompts: list[str], clip_model, clip_preprocess, clip_tokenizer, device: str) -> list[float]:
    import torch
    from PIL import Image

    image = Image.open(image_path).convert("RGB")
    image_input = clip_preprocess(image).unsqueeze(0).to(device)
    text_inputs = clip_tokenizer(text_prompts, padding=True, return_tensors="pt").to(device)

    with torch.no_grad():
        image_features = clip_model.encode_image(image_input)
        text_features = clip_model.encode_text(text_inputs)
        image_features = image_features / image_features.norm(dim=-1, keepdim=True)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        similarities = (image_features @ text_features.T).squeeze(0).cpu().tolist()

    return similarities


def main():
    parser = argparse.ArgumentParser(description="Auto-label frames with YOLO + CLIP")
    parser.add_argument("--frames", type=Path, default=Path("data/frames"))
    parser.add_argument("--output", type=Path, default=Path("data/auto_labels"))
    parser.add_argument("--yolo-threshold", type=float, default=0.4)
    parser.add_argument("--clip-threshold", type=float, default=0.28)
    args = parser.parse_args()

    from ultralytics import YOLO
    yolo = YOLO("yolov8n.pt")

    try:
        import clip
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        clip_model, clip_preprocess = clip.load("ViT-B/32", device=device)
        clip_tokenizer = clip.tokenize
        use_clip = True
        print("Using YOLO + CLIP for detection")
    except Exception as e:
        print(f"CLIP not available ({e}), using YOLO only (person class)")
        use_clip = False

    images = sorted(args.frames.glob("*.jpg")) + sorted(args.frames.glob("*.png"))
    args.output.mkdir(parents=True, exist_ok=True)

    for img_path in images:
        frame = cv2.imread(str(img_path))
        if frame is None:
            continue

        yolo_dets = detect_with_yolo(frame, yolo)
        lines = []

        for det in yolo_dets:
            if det["class"] == "person" and det["confidence"] >= args.yolo_threshold:
                x1, y1, x2, y2 = det["bbox"]
                h, w = frame.shape[:2]
                cx = ((x1 + x2) / 2) / w
                cy = ((y1 + y2) / 2) / h
                bw = (x2 - x1) / w
                bh = (y2 - y1) / h
                lines.append(f"0 {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")

        if use_clip:
            sims = compute_clip_similarity(str(img_path), ["photo of " + p for prompts in CLASS_PROMPTS.values() for p in prompts], clip_model, clip_preprocess, clip_tokenizer, device)

            prompt_idx = 0
            for cls_name, prompts in CLASS_PROMPTS.items():
                if cls_name == "person":
                    prompt_idx += len(prompts)
                    continue
                cls_sims = sims[prompt_idx : prompt_idx + len(prompts)]
                max_sim = max(cls_sims)
                if max_sim >= args.clip_threshold:
                    lines.append(f"{CLASS_TO_ID[cls_name]} 0.5 0.5 0.3 0.3")
                prompt_idx += len(prompts)

        label_path = args.output / f"{img_path.stem}.txt"
        label_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"{img_path.name}: {len(lines)} labels")

    print(f"\nDone. Labels saved to {args.output}")
    print("Review and correct, then run: python src/convert_to_yolo.py")


if __name__ == "__main__":
    main()
