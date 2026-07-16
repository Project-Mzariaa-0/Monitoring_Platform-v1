"""
Data augmentation for time-series action recognition sequences.

Augmentations:
1. Time shift — shift sequence start ±N frames
2. Speed variation — resample frames at slightly different rates
3. Feature noise — add Gaussian noise to features
4. Random crop — extract random sub-sequence
5. Feature masking — randomly zero out feature dimensions
6. Temporal dropout — randomly zero out entire timesteps
"""

import numpy as np
from typing import List, Tuple


class SequenceAugmenter:
    """Augments (seq_len, n_features) sequences for training."""

    def __init__(
        self,
        time_shift_max: int = 3,
        speed_range: Tuple[float, float] = (0.9, 1.1),
        noise_std: float = 0.05,
        crop_ratio: float = 0.8,
        feature_mask_ratio: float = 0.1,
        temporal_dropout_ratio: float = 0.05,
        seed: int = 42,
    ):
        self.time_shift_max = time_shift_max
        self.speed_range = speed_range
        self.noise_std = noise_std
        self.crop_ratio = crop_ratio
        self.feature_mask_ratio = feature_mask_ratio
        self.temporal_dropout_ratio = temporal_dropout_ratio
        self.rng = np.random.RandomState(seed)

    def augment(self, sequence: np.ndarray, n_augmented: int = 4) -> List[np.ndarray]:
        """Generate n_augmented variations of a sequence."""
        seq_len, n_features = sequence.shape
        results = [sequence.copy()]

        for _ in range(n_augmented):
            aug = sequence.copy()
            method = self.rng.choice(["shift", "speed", "noise", "crop", "mask", "temporal"])

            if method == "shift":
                aug = self._time_shift(aug)
            elif method == "speed":
                aug = self._speed_variation(aug)
            elif method == "noise":
                aug = self._feature_noise(aug)
            elif method == "crop":
                aug = self._random_crop(aug)
            elif method == "mask":
                aug = self._feature_masking(aug)
            elif method == "temporal":
                aug = self._temporal_dropout(aug)

            results.append(aug)

        return results

    def _time_shift(self, seq: np.ndarray) -> np.ndarray:
        shift = self.rng.randint(-self.time_shift_max, self.time_shift_max + 1)
        if shift > 0:
            return np.roll(seq, shift, axis=0)
        elif shift < 0:
            return np.roll(seq, shift, axis=0)
        return seq

    def _speed_variation(self, seq: np.ndarray) -> np.ndarray:
        speed = self.rng.uniform(*self.speed_range)
        seq_len = seq.shape[0]
        indices = np.linspace(0, seq_len - 1, int(seq_len * speed))
        indices = np.clip(indices, 0, seq_len - 1).astype(int)
        resampled = seq[indices]
        if resampled.shape[0] >= seq_len:
            return resampled[:seq_len]
        pad = np.tile(resampled[-1:], (seq_len - resampled.shape[0], 1))
        return np.concatenate([resampled, pad], axis=0)

    def _feature_noise(self, seq: np.ndarray) -> np.ndarray:
        noise = self.rng.normal(0, self.noise_std, seq.shape).astype(np.float32)
        return np.clip(seq + noise, -1.0, 1.0)

    def _random_crop(self, seq: np.ndarray) -> np.ndarray:
        seq_len = seq.shape[0]
        crop_len = int(seq_len * self.crop_ratio)
        start = self.rng.randint(0, seq_len - crop_len + 1)
        cropped = seq[start:start + crop_len]
        if cropped.shape[0] >= seq_len:
            return cropped[:seq_len]
        pad = np.tile(cropped[-1:], (seq_len - cropped.shape[0], 1))
        return np.concatenate([cropped, pad], axis=0)

    def _feature_masking(self, seq: np.ndarray) -> np.ndarray:
        n_features = seq.shape[1]
        n_mask = max(1, int(n_features * self.feature_mask_ratio))
        mask_indices = self.rng.choice(n_features, n_mask, replace=False)
        aug = seq.copy()
        aug[:, mask_indices] = 0.0
        return aug

    def _temporal_dropout(self, seq: np.ndarray) -> np.ndarray:
        seq_len = seq.shape[0]
        n_drop = max(1, int(seq_len * self.temporal_dropout_ratio))
        drop_indices = self.rng.choice(seq_len, n_drop, replace=False)
        aug = seq.copy()
        aug[drop_indices] = 0.0
        return aug


def augment_dataset(
    sequences: np.ndarray,
    labels: np.ndarray,
    n_augmented: int = 4,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """Augment entire dataset. Returns (augmented_sequences, augmented_labels)."""
    augmenter = SequenceAugmenter(seed=seed)

    all_sequences = []
    all_labels = []

    for i in range(len(sequences)):
        augs = augmenter.augment(sequences[i], n_augmented=n_augmented)
        for aug_seq in augs:
            all_sequences.append(aug_seq)
            all_labels.append(labels[i])

    return np.array(all_sequences), np.array(all_labels)
