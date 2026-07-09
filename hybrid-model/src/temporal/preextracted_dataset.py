"""
Dataset for pre-extracted features.
"""

import os
import json
import numpy as np
import torch
from torch.utils.data import Dataset
from pathlib import Path
from typing import Tuple, List


class PreExtractedDataset(Dataset):
    """
    Dataset using pre-extracted YOLO features.
    """
    
    def __init__(
        self,
        features_dir: str,
        annotations_dir: str,
        split_file: str,
        sequence_length: int = 30
    ):
        """
        Initialize dataset.
        
        Args:
            features_dir: Directory with .npy feature files
            annotations_dir: Directory with annotation JSONs
            split_file: Path to split file (train/val/test)
            sequence_length: Number of frames per sequence
        """
        self.features_dir = Path(features_dir)
        self.annotations_dir = Path(annotations_dir)
        self.sequence_length = sequence_length
        
        # Load split
        with open(split_file, 'r') as f:
            self.video_ids = [line.strip() for line in f if line.strip()]
        
        # Create sequences
        self.sequences = self._create_sequences()
    
    def _create_sequences(self) -> List[dict]:
        """Create training sequences from annotations."""
        sequences = []
        
        for video_id in self.video_ids:
            # Load features
            features_path = self.features_dir / f"{video_id}_features.npy"
            if not features_path.exists():
                continue
            
            features = np.load(features_path)
            num_frames = len(features)
            
            # Load annotations
            ann_path = self.annotations_dir / video_id / "annotations.json"
            if not ann_path.exists():
                continue
            
            with open(ann_path, 'r') as f:
                annotations = json.load(f)
            
            # Create sequences for each task
            for task in annotations.get("tasks", []):
                task_id = task["id"]
                start_frame = task["start_frame"]
                end_frame = task["end_frame"]
                
                # Label mapping
                label_map = {
                    "TASK-01": 0,
                    "TASK-02": 1,
                    "TASK-03": 2,
                    "TASK-04": 3,
                    "TASK-05": 4,
                    "TASK-06": 5
                }
                
                if task_id not in label_map:
                    continue
                
                label = label_map[task_id]
                
                # Create overlapping sequences
                for seq_start in range(
                    max(0, start_frame - self.sequence_length + 1),
                    min(end_frame, num_frames - self.sequence_length + 1),
                    self.sequence_length // 2  # 50% overlap
                ):
                    sequences.append({
                        "video_id": video_id,
                        "start_frame": seq_start,
                        "label": label
                    })
        
        return sequences
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        seq_info = self.sequences[idx]
        video_id = seq_info["video_id"]
        start_frame = seq_info["start_frame"]
        label = seq_info["label"]
        
        # Load features
        features_path = self.features_dir / f"{video_id}_features.npy"
        features = np.load(features_path)
        
        # Extract sequence
        sequence = features[start_frame:start_frame + self.sequence_length]
        
        # Pad if needed
        if len(sequence) < self.sequence_length:
            padding = np.zeros((self.sequence_length - len(sequence), features.shape[1]))
            sequence = np.concatenate([sequence, padding], axis=0)
        
        return torch.FloatTensor(sequence), torch.LongTensor([label])[0]


def create_dataloaders(
    features_dir: str,
    annotations_dir: str,
    splits_dir: str,
    batch_size: int = 32,
    sequence_length: int = 30
):
    """Create train/val/test dataloaders."""
    from torch.utils.data import DataLoader
    
    train_dataset = PreExtractedDataset(
        features_dir=features_dir,
        annotations_dir=annotations_dir,
        split_file=os.path.join(splits_dir, "train.txt"),
        sequence_length=sequence_length
    )
    
    val_dataset = PreExtractedDataset(
        features_dir=features_dir,
        annotations_dir=annotations_dir,
        split_file=os.path.join(splits_dir, "val.txt"),
        sequence_length=sequence_length
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )
    
    return train_loader, val_loader
