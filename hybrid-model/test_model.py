"""
Quick inference test for the trained LSTM model.
"""

import sys
import numpy as np
import cv2
import torch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from detection.enhanced_yolo import EnhancedYOLODetector
from temporal.lstm_model import MilkingActionLSTM

TASK_NAMES = {
    0: "TASK-01 Pre-cleaning",
    1: "TASK-02 Stripping",
    2: "TASK-03 Attachment",
    3: "TASK-04 Milking",
    4: "TASK-05 Detachment",
    5: "TASK-06 Post-dip",
}

SEQUENCE_LENGTH = 30


def test_video(video_path: str, model_path: str = "models/checkpoints/best_model.pt"):
    """Run inference on a video file."""
    config = load_config("configs/default.yaml")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model
    checkpoint = torch.load(model_path, map_location=device)
    model_config = checkpoint['config']
    model = MilkingActionLSTM(
        input_size=model_config['input_size'],
        hidden_size=model_config['hidden_size'],
        num_layers=model_config['num_layers'],
        num_classes=model_config['num_classes'],
        dropout=model_config['dropout'],
        bidirectional=model_config['bidirectional']
    ).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Load YOLO detector
    detector = EnhancedYOLODetector(config)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    print(f"Video: {video_path}")
    print(f"FPS: {fps:.1f}, Duration: {duration:.1f}s, Total frames: {total_frames}")
    print("-" * 60)

    # Extract features from all frames
    all_features = []
    frame_idx = 0
    frame_skip = max(1, int(fps / 5))  # 5 fps

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_skip == 0:
            # Don't resize - let YOLO handle native resolution with imgsz=1280
            frame_features = detector.extract_features(frame, frame_idx)
            all_features.append(frame_features.feature_vector)

        frame_idx += 1

    cap.release()

    if not all_features:
        print("No frames extracted!")
        return

    features = np.array(all_features)
    print(f"Extracted {len(features)} frames")
    print("-" * 60)

    # Run inference on sliding windows
    num_sequences = max(1, len(features) - SEQUENCE_LENGTH + 1)
    step = max(1, SEQUENCE_LENGTH // 2)  # 50% overlap

    predictions = []
    for start in range(0, len(features) - SEQUENCE_LENGTH + 1, step):
        seq = features[start:start + SEQUENCE_LENGTH]
        seq_tensor = torch.FloatTensor(seq).unsqueeze(0).to(device)

        with torch.no_grad():
            output, _ = model(seq_tensor)
            probs = torch.softmax(output, dim=1)
            pred_class = torch.argmax(probs, dim=1).item()
            confidence = probs[0][pred_class].item()

        predictions.append({
            "start_frame": start,
            "end_frame": start + SEQUENCE_LENGTH,
            "task_id": pred_class,
            "task_name": TASK_NAMES.get(pred_class, f"Unknown-{pred_class}"),
            "confidence": confidence,
            "probs": probs[0].cpu().numpy()
        })

    # Print predictions
    print(f"{'Frame Range':<20} {'Prediction':<30} {'Confidence':<12}")
    print("-" * 62)

    for pred in predictions:
        frame_range = f"{pred['start_frame']}-{pred['end_frame']}"
        print(f"{frame_range:<20} {pred['task_name']:<30} {pred['confidence']:.1%}")

    # Summary
    print("\n" + "=" * 62)
    print("SUMMARY")
    print("=" * 62)

    task_counts = {}
    for pred in predictions:
        task_name = pred['task_name']
        task_counts[task_name] = task_counts.get(task_name, 0) + 1

    for task_name, count in sorted(task_counts.items()):
        pct = 100.0 * count / len(predictions)
        print(f"{task_name:<30} {count:>4} sequences ({pct:.1f}%)")

    # Show per-class probabilities
    print("\nAVERAGE CONFIDENCE PER CLASS:")
    print("-" * 40)
    avg_probs = np.mean([p['probs'] for p in predictions], axis=0)
    for i, (task_name, prob) in enumerate(zip(TASK_NAMES.values(), avg_probs)):
        bar = "#" * int(prob * 30)
        print(f"{task_name:<30} {prob:.1%} {bar}")


def test_frame(frame_path: str, model_path: str = "models/checkpoints/best_model.pt"):
    """Run inference on a single frame (with context from surrounding frames)."""
    config = load_config("configs/default.yaml")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Load model
    checkpoint = torch.load(model_path, map_location=device)
    model_config = checkpoint['config']
    model = MilkingActionLSTM(
        input_size=model_config['input_size'],
        hidden_size=model_config['hidden_size'],
        num_layers=model_config['num_layers'],
        num_classes=model_config['num_classes'],
        dropout=model_config['dropout'],
        bidirectional=model_config['bidirectional']
    ).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # Load YOLO detector
    detector = EnhancedYOLODetector(config)

    # Load and process frame
    frame = cv2.imread(frame_path)
    if frame is None:
        print(f"Error: Could not load {frame_path}")
        return

    # Don't resize - let YOLO handle native resolution with imgsz=1280
    features = detector.extract_features(frame, 0)

    # Create a sequence by repeating the same frame (for single frame inference)
    seq = np.tile(features.feature_vector, (SEQUENCE_LENGTH, 1))
    seq_tensor = torch.FloatTensor(seq).unsqueeze(0).to(device)

    with torch.no_grad():
        output, _ = model(seq_tensor)
        probs = torch.softmax(output, dim=1)
        pred_class = torch.argmax(probs, dim=1).item()
        confidence = probs[0][pred_class].item()

    print(f"Frame: {frame_path}")
    print(f"Prediction: {TASK_NAMES[pred_class]} (confidence: {confidence:.1%})")
    print("\nAll class probabilities:")
    for i, (task_name, prob) in enumerate(zip(TASK_NAMES.values(), probs[0])):
        bar = "#" * int(prob * 30)
        print(f"  {task_name:<30} {prob:.1%} {bar}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test trained model")
    parser.add_argument("input", type=str, help="Video file or image file")
    parser.add_argument("--model", type=str, default="models/checkpoints/best_model.pt",
                        help="Model checkpoint path")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    # Check if video or image
    video_exts = {'.mp4', '.mov', '.avi', '.mkv'}
    image_exts = {'.jpg', '.jpeg', '.png', '.bmp'}

    if input_path.suffix.lower() in video_exts:
        test_video(str(input_path), args.model)
    elif input_path.suffix.lower() in image_exts:
        test_frame(str(input_path), args.model)
    else:
        print(f"Unknown file type: {input_path.suffix}")
        sys.exit(1)
