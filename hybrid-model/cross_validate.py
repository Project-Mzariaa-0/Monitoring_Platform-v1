"""
Stratified K-Fold cross-validation for the hybrid model.
Reports mean ± std accuracy across folds.
"""

import sys
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from torch.utils.data import DataLoader, Dataset
from sklearn.model_selection import StratifiedKFold

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import load_config
from temporal.lstm_model import MilkingActionLSTM
from training.augmentation import augment_dataset

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SequenceDataset(Dataset):
    def __init__(self, features, labels):
        self.features = torch.FloatTensor(features)
        self.labels = torch.LongTensor(labels)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


def train_fold(config, train_features, train_labels, val_features, val_labels, epochs=60):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Augment training data
    aug_features, aug_labels = augment_dataset(train_features, train_labels, n_augmented=8, seed=42)

    train_dataset = SequenceDataset(aug_features, aug_labels)
    val_dataset = SequenceDataset(val_features, val_labels)

    batch_size = min(32, len(train_dataset))
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model = MilkingActionLSTM(
        input_size=config.lstm.input_size,
        hidden_size=config.lstm.hidden_size,
        num_layers=config.lstm.num_layers,
        num_classes=config.lstm.num_classes,
        dropout=config.lstm.dropout,
        bidirectional=config.lstm.bidirectional
    ).to(device)

    # Class weights
    unique_labels = np.unique(aug_labels).astype(int)
    class_counts = np.bincount(aug_labels.astype(int))
    class_weights = np.ones(config.lstm.num_classes, dtype=np.float64)
    for lbl in unique_labels:
        if lbl < config.lstm.num_classes:
            class_weights[lbl] = len(aug_labels) / (class_counts[lbl] * config.lstm.num_classes)
    class_weights = np.clip(class_weights, 0.1, 10.0)
    class_weights_tensor = torch.FloatTensor(class_weights).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)

    optimizer = torch.optim.Adam(model.parameters(), lr=config.training.learning_rate, weight_decay=config.training.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_acc = 0.0
    patience = 15
    patience_counter = 0

    for epoch in range(epochs):
        model.train()
        for features, labels in train_loader:
            features, labels = features.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs, _ = model(features)
            loss = criterion(outputs, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        scheduler.step()

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs, _ = model(features)
                _, predicted = torch.max(outputs.data, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_acc = 100.0 * val_correct / val_total if val_total > 0 else 0

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                break

    return best_val_acc


def main():
    config = load_config()

    processed_path = Path("data/processed_v2")
    all_features = np.load(str(processed_path / "all_sequences.npy"))
    all_labels = np.load(str(processed_path / "all_labels.npy"))

    logger.info(f"Data: {all_features.shape}, Labels: {len(np.unique(all_labels))} classes")

    # Stratified 5-fold cross-validation
    n_folds = 5
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=42)

    fold_accs = []
    for fold, (train_idx, val_idx) in enumerate(skf.split(all_features, all_labels)):
        logger.info(f"\n--- Fold {fold+1}/{n_folds} ---")
        logger.info(f"  Train: {len(train_idx)}, Val: {len(val_idx)}")

        acc = train_fold(
            config,
            all_features[train_idx], all_labels[train_idx],
            all_features[val_idx], all_labels[val_idx],
        )
        fold_accs.append(acc)
        logger.info(f"  Fold {fold+1} Best Val Acc: {acc:.2f}%")

    mean_acc = np.mean(fold_accs)
    std_acc = np.std(fold_accs)

    logger.info(f"\n{'='*60}")
    logger.info(f"CROSS-VALIDATION RESULTS ({n_folds} folds)")
    logger.info(f"Mean Val Acc: {mean_acc:.2f}% ± {std_acc:.2f}%")
    logger.info(f"Per-fold: {[f'{a:.1f}' for a in fold_accs]}")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
