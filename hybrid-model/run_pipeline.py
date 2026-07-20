"""
Full pipeline: Extract frames → Extract features → Annotate → Split → Train
"""

import os
import sys
import json
import shutil
import numpy as np
import cv2
from pathlib import Path
from tqdm import tqdm
import logging
import yaml

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config, ModelConfig
from detection.multimodal_feature_extractor import MultimodalFeatureExtractor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Task mapping
TASK_MAP = {
    "task_01_precleaning": {"id": "TASK-01", "label": 0, "name": "Pre-cleaning"},
    "task_02_stripping": {"id": "TASK-02", "label": 1, "name": "Stripping"},
    "task_03_attachment": {"id": "TASK-03", "label": 2, "name": "Attachment"},
    "task_04_milking": {"id": "TASK-04", "label": 3, "name": "Milking"},
    "task_05_detachment": {"id": "TASK-05", "label": 4, "name": "Detachment"},
    "task_06_postdip": {"id": "TASK-06", "label": 5, "name": "Post-dip"},
}

SEQUENCE_LENGTH = 30  # default, overridden by --seq-length


def step1_extract_frames(raw_dir: str, output_dir: str, target_fps: int = 5):
    """Extract frames from all video clips."""
    logger.info("=" * 60)
    logger.info("STEP 1: Extracting frames from videos")
    logger.info("=" * 60)

    raw_path = Path(raw_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    video_count = 0
    total_frames = 0

    for task_dir in sorted(raw_path.iterdir()):
        if not task_dir.is_dir():
            continue

        task_name = task_dir.name
        if task_name not in TASK_MAP:
            continue

        task_info = TASK_MAP[task_name]
        task_output = output_path / task_name
        task_output.mkdir(parents=True, exist_ok=True)

        videos = list(task_dir.glob("*.mov")) + list(task_dir.glob("*.mp4"))
        if not videos:
            logger.warning(f"No videos found in {task_dir}")
            continue

        for video_path in videos:
            logger.info(f"Processing: {video_path.name} -> {task_info['name']}")

            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                logger.error(f"Could not open: {video_path}")
                continue

            original_fps = cap.get(cv2.CAP_PROP_FPS)
            total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_video_frames / original_fps if original_fps > 0 else 0

            logger.info(f"  FPS: {original_fps:.1f}, Duration: {duration:.1f}s, Total frames: {total_video_frames}")

            frame_skip = max(1, int(original_fps / target_fps))
            frame_idx = 0
            saved_count = 0

            clip_name = video_path.stem

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % frame_skip == 0:
                    frame_filename = f"{clip_name}_frame_{saved_count:06d}.jpg"
                    frame_path = task_output / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    saved_count += 1

                frame_idx += 1

            cap.release()
            total_frames += saved_count
            video_count += 1
            logger.info(f"  Saved {saved_count} frames at {target_fps} fps")

    logger.info(f"\nTotal: {video_count} videos, {total_frames} frames extracted")
    return total_frames


def step2_extract_features(config: ModelConfig, frames_dir: str, features_dir: str, seq_len: int = 30):
    """Extract multimodal sequence features from all frames.

    Runs both YOLOv8-Pose (512-dim) and YOLOv8n (128-dim) on each frame,
    producing a combined 640-dim feature vector per frame.
    Each clip produces one (seq_len, 640) sequence.
    """
    logger.info("=" * 60)
    logger.info("STEP 2: Extracting multimodal features (pose 512 + objects 128 = 640 dims)")
    logger.info("=" * 60)

    detector = MultimodalFeatureExtractor(config)
    frames_path = Path(frames_dir)
    features_path = Path(features_dir)
    features_path.mkdir(parents=True, exist_ok=True)

    all_features = {}
    total_frames = 0

    for task_dir in sorted(frames_path.iterdir()):
        if not task_dir.is_dir():
            continue

        task_name = task_dir.name
        if task_name not in TASK_MAP:
            continue

        task_info = TASK_MAP[task_name]
        logger.info(f"Extracting features for: {task_info['name']}")

        frame_files = sorted(task_dir.glob("*.jpg"))
        if not frame_files:
            continue

        # Load all frames for this task
        frames = []
        for frame_file in tqdm(frame_files, desc=f"  Loading {task_info['name']}"):
            frame = cv2.imread(str(frame_file))
            if frame is not None:
                frame_resized = cv2.resize(frame, (640, 640))
                frames.append(frame_resized)

        if not frames:
            continue

        # Process in chunks of seq_len
        sequences = []
        metadata = []
        for chunk_start in range(0, len(frames), seq_len):
            chunk = frames[chunk_start : chunk_start + seq_len]
            if len(chunk) < 2:
                continue  # need at least 2 frames for motion

            seq_features = detector.extract_sequence_features(chunk)  # (chunk_len, 512)

            # Pad shorter sequences to seq_len
            if len(seq_features) < seq_len:
                pad = np.zeros((seq_len - len(seq_features), 640))
                seq_features = np.concatenate([seq_features, pad], axis=0)

            sequences.append(seq_features)

            metadata.append({
                "task_id": task_info["id"],
                "task_label": task_info["label"],
                "chunk_start": chunk_start,
                "chunk_end": chunk_start + len(chunk),
                "num_frames": len(chunk),
                "feature_shape": list(seq_features.shape),
            })

        if sequences:
            features_array = np.array(sequences)  # (num_seqs, seq_len, 512)
            task_features_file = features_path / f"{task_name}_features.npy"
            np.save(str(task_features_file), features_array)

            metadata_file = features_path / f"{task_name}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)

            all_features[task_name] = {
                "num_sequences": len(sequences),
                "seq_len": seq_len,
                "feature_dim": features_array.shape[2],
                "total_frames": sum(m["num_frames"] for m in metadata),
            }
            total_frames += sum(m["num_frames"] for m in metadata)
            logger.info(f"  {len(sequences)} sequences, shape: {features_array.shape}")

    summary_file = features_path / "extraction_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_features, f, indent=2)

    logger.info(f"\nTotal: {total_frames} frames in {sum(v['num_sequences'] for v in all_features.values())} sequences")
    return all_features


def step3_create_annotations(features_dir: str, processed_dir: str):
    """Create training sequences from extracted features.

    Features are already stored as (num_seqs, seq_len, 512) sequences.
    This step just combines all tasks and creates labels.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: Creating annotations and training sequences")
    logger.info("=" * 60)

    features_path = Path(features_dir)
    processed_path = Path(processed_dir)
    processed_path.mkdir(parents=True, exist_ok=True)

    all_features_combined = []
    all_labels = []
    sequences = []

    for task_dir_name in sorted(TASK_MAP.keys()):
        task_info = TASK_MAP[task_dir_name]
        features_file = features_path / f"{task_dir_name}_features.npy"

        if not features_file.exists():
            logger.warning(f"Features not found for {task_dir_name}, skipping")
            continue

        features = np.load(str(features_file))  # (num_seqs, seq_len, 512)
        num_seqs = len(features)

        logger.info(f"{task_info['name']}: {num_seqs} sequences, shape {features.shape}")

        for i in range(num_seqs):
            all_features_combined.append(features[i])
            all_labels.append(task_info["label"])
            sequences.append({
                "task_dir": task_dir_name,
                "task_id": task_info["id"],
                "task_label": task_info["label"],
                "task_name": task_info["name"],
                "sequence_idx": i,
            })

    # Save all sequences
    if all_features_combined:
        all_features_array = np.array(all_features_combined)
        all_labels_array = np.array(all_labels)

        np.save(str(processed_path / "all_sequences.npy"), all_features_array)
        np.save(str(processed_path / "all_labels.npy"), all_labels_array)

        with open(processed_path / "sequences.json", 'w') as f:
            json.dump(sequences, f, indent=2)

        task_counts = {}
        for s in sequences:
            task_id = s["task_id"]
            task_counts[task_id] = task_counts.get(task_id, 0) + 1

        logger.info(f"\nTotal sequences: {len(sequences)}")
        for task_id, count in sorted(task_counts.items()):
            logger.info(f"  {task_id}: {count} sequences")

        return sequences
    else:
        logger.error("No sequences created!")
        return []


def step4_split_data(processed_dir: str, splits_dir: str, val_ratio: float = 0.2):
    """Split data into train/val sets."""
    logger.info("=" * 60)
    logger.info("STEP 4: Splitting data into train/val")
    logger.info("=" * 60)

    processed_path = Path(processed_dir)
    splits_path = Path(splits_dir)
    splits_path.mkdir(parents=True, exist_ok=True)

    sequences_file = processed_path / "sequences.json"
    if not sequences_file.exists():
        logger.error("sequences.json not found!")
        return

    with open(sequences_file, 'r') as f:
        sequences = json.load(f)

    # Group by task for stratified split
    task_sequences = {}
    for i, seq in enumerate(sequences):
        task_id = seq["task_id"]
        if task_id not in task_sequences:
            task_sequences[task_id] = []
        task_sequences[task_id].append(i)

    train_indices = []
    val_indices = []

    for task_id, indices in task_sequences.items():
        np.random.shuffle(indices)
        split_point = int(len(indices) * (1 - val_ratio))
        train_indices.extend(indices[:split_point])
        val_indices.extend(indices[split_point:])

    np.random.shuffle(train_indices)
    np.random.shuffle(val_indices)

    # Save splits
    with open(splits_path / "train.txt", 'w') as f:
        for idx in train_indices:
            f.write(f"{idx}\n")

    with open(splits_path / "val.txt", 'w') as f:
        for idx in val_indices:
            f.write(f"{idx}\n")

    logger.info(f"Train: {len(train_indices)} sequences")
    logger.info(f"Val: {len(val_indices)} sequences")

    return train_indices, val_indices


def step5_train_model(config: ModelConfig, processed_dir: str, splits_dir: str):
    """Train the LSTM model."""
    logger.info("=" * 60)
    logger.info("STEP 5: Training LSTM model")
    logger.info("=" * 60)

    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from temporal.lstm_model import MilkingActionLSTM

    processed_path = Path(processed_dir)

    # Load data
    all_features = np.load(str(processed_path / "all_sequences.npy"))
    all_labels = np.load(str(processed_path / "all_labels.npy"))

    # Load splits
    splits_path = Path(splits_dir)
    with open(splits_path / "train.txt", 'r') as f:
        train_indices = [int(line.strip()) for line in f if line.strip()]
    with open(splits_path / "val.txt", 'r') as f:
        val_indices = [int(line.strip()) for line in f if line.strip()]

    # Augment training data
    from training.augmentation import augment_dataset
    train_features = all_features[train_indices]
    train_labels = all_labels[train_indices]
    aug_features, aug_labels = augment_dataset(train_features, train_labels, n_augmented=8, seed=42)
    logger.info(f"Original train: {len(train_indices)} -> Augmented: {len(aug_labels)}")

    logger.info(f"Train sequences: {len(aug_labels)}")
    logger.info(f"Val sequences: {len(val_indices)}")
    logger.info(f"Feature shape: {aug_features.shape}")
    logger.info(f"Num classes: {len(np.unique(all_labels))}")

    # Custom dataset
    class SequenceDataset(Dataset):
        def __init__(self, features, labels):
            self.features = torch.FloatTensor(features)
            self.labels = torch.LongTensor(labels)

        def __len__(self):
            return len(self.features)

        def __getitem__(self, idx):
            return self.features[idx], self.labels[idx]

    train_dataset = SequenceDataset(aug_features, aug_labels)
    val_dataset = SequenceDataset(all_features[val_indices], all_labels[val_indices])

    batch_size = min(config.training.batch_size, len(train_dataset))
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    # Initialize model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Device: {device}")

    model = MilkingActionLSTM(
        input_size=config.lstm.input_size,
        hidden_size=config.lstm.hidden_size,
        num_layers=config.lstm.num_layers,
        num_classes=config.lstm.num_classes,
        dropout=config.lstm.dropout,
        bidirectional=config.lstm.bidirectional
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {total_params:,}")

    # Loss, optimizer, scheduler — weighted to handle class imbalance
    unique_labels = np.unique(aug_labels).astype(int)
    class_counts = np.bincount(aug_labels.astype(int))
    # Compute weights only for classes that exist, map back to full range
    class_weights = np.ones(config.lstm.num_classes, dtype=np.float64)
    for lbl in unique_labels:
        if lbl < config.lstm.num_classes:
            class_weights[lbl] = len(aug_labels) / (class_counts[lbl] * config.lstm.num_classes)
    class_weights = np.clip(class_weights, 0.1, 10.0)
    class_weights_tensor = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    logger.info(f"Class weights: {dict(zip(range(config.lstm.num_classes), [f'{w:.3f}' for w in class_weights]))}")
    optimizer = optim.Adam(model.parameters(), lr=config.training.learning_rate, weight_decay=config.training.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config.training.epochs)

    # Training loop
    best_val_acc = 0.0
    patience_counter = 0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}

    models_dir = Path(config.models_dir)
    checkpoints_dir = Path(config.checkpoints_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(config.training.epochs):
        # Train
        model.train()
        total_loss = 0.0
        correct = 0
        total = 0

        for features, labels in train_loader:
            features = features.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()
            outputs, _ = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_loss = total_loss / len(train_loader)
        train_acc = 100.0 * correct / total

        # Validate
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for features, labels in val_loader:
                features = features.to(device)
                labels = labels.to(device)
                outputs, _ = model(features)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_loss = val_loss / len(val_loader) if len(val_loader) > 0 else 0
        val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0

        scheduler.step()

        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)

        logger.info(f"Epoch {epoch+1}/{config.training.epochs} - "
                    f"Train Loss: {train_loss:.4f}, Acc: {train_acc:.2f}% | "
                    f"Val Loss: {val_loss:.4f}, Acc: {val_acc:.2f}%")

        # Save best
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
            torch.save({
                'model_state_dict': model.state_dict(),
                'config': {
                    'input_size': config.lstm.input_size,
                    'hidden_size': config.lstm.hidden_size,
                    'num_layers': config.lstm.num_layers,
                    'num_classes': config.lstm.num_classes,
                    'dropout': config.lstm.dropout,
                    'bidirectional': config.lstm.bidirectional,
                }
            }, str(checkpoints_dir / "best_model.pt"))
            logger.info(f"  -> New best model! Val Acc: {val_acc:.2f}%")
        else:
            patience_counter += 1

        if config.training.early_stopping_enabled and patience_counter >= config.training.early_stopping_patience:
            logger.info(f"Early stopping at epoch {epoch+1}")
            break

    # Save final model and history
    torch.save({
        'model_state_dict': model.state_dict(),
        'config': {
            'input_size': config.lstm.input_size,
            'hidden_size': config.lstm.hidden_size,
            'num_layers': config.lstm.num_layers,
            'num_classes': config.lstm.num_classes,
            'dropout': config.lstm.dropout,
            'bidirectional': config.lstm.bidirectional,
        }
    }, str(checkpoints_dir / "final_model.pt"))

    with open(models_dir / "training_history.json", 'w') as f:
        json.dump(history, f, indent=2)

    logger.info(f"\nTraining complete! Best Val Acc: {best_val_acc:.2f}%")
    logger.info(f"Models saved to: {models_dir}")

    return best_val_acc


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Full training pipeline")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--raw-dir", type=str, default="data/raw")
    parser.add_argument("--frames-dir", type=str, default="data/frames")
    parser.add_argument("--features-dir", type=str, default="data/features_v2")
    parser.add_argument("--processed-dir", type=str, default="data/processed_v2")
    parser.add_argument("--splits-dir", type=str, default="data/splits_v2")
    parser.add_argument("--fps", type=int, default=5)
    parser.add_argument("--seq-length", type=int, default=30, help="Sequence length for motion features")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--skip-frames", action="store_true", help="Skip frame extraction")
    parser.add_argument("--skip-features", action="store_true", help="Skip feature extraction")

    args = parser.parse_args()

    config = load_config(args.config)
    if args.epochs:
        config.training.epochs = args.epochs

    base_dir = Path(__file__).parent

    # Step 1: Extract frames
    if not args.skip_frames:
        step1_extract_frames(
            str(base_dir / args.raw_dir),
            str(base_dir / args.frames_dir),
            target_fps=args.fps
        )
    else:
        logger.info("Skipping frame extraction")

    # Step 2: Extract features
    if not args.skip_features:
        step2_extract_features(
            config,
            str(base_dir / args.frames_dir),
            str(base_dir / args.features_dir),
            seq_len=args.seq_length,
        )
    else:
        logger.info("Skipping feature extraction")

    # Step 3: Create annotations
    step3_create_annotations(
        str(base_dir / args.features_dir),
        str(base_dir / args.processed_dir)
    )

    # Step 4: Split data
    step4_split_data(
        str(base_dir / args.processed_dir),
        str(base_dir / args.splits_dir)
    )

    # Step 5: Train model
    best_acc = step5_train_model(
        config,
        str(base_dir / args.processed_dir),
        str(base_dir / args.splits_dir)
    )

    logger.info(f"\n{'=' * 60}")
    logger.info(f"PIPELINE COMPLETE")
    logger.info(f"Best Validation Accuracy: {best_acc:.2f}%")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
