"""
Dataset for loading video sequences for LSTM training.
"""

import os
import json
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2


class MilkingSequenceDataset(Dataset):
    """
    Dataset for loading video sequences with annotations.
    
    Expected directory structure:
    data/
    ├── processed/
    │   ├── video_001/
    │   │   ├── frames/
    │   │   │   ├── 0000.jpg
    │   │   │   ├── 0001.jpg
    │   │   │   └── ...
    │   │   └── annotations.json
    │   └── ...
    └── splits/
        ├── train.txt
        ├── val.txt
        └── test.txt
    """
    
    def __init__(
        self,
        data_dir: str,
        split: str = "train",
        sequence_length: int = 30,
        feature_extractor=None,
        transform=None
    ):
        """
        Initialize the dataset.
        
        Args:
            data_dir: Path to processed data directory
            split: "train", "val", or "test"
            sequence_length: Number of frames per sequence
            feature_extractor: YOLOFeatureExtractor instance
            transform: Optional transform to apply to frames
        """
        self.data_dir = Path(data_dir)
        self.split = split
        self.sequence_length = sequence_length
        self.feature_extractor = feature_extractor
        self.transform = transform
        
        # Load split file
        split_file = self.data_dir.parent / "splits" / f"{split}.txt"
        if split_file.exists():
            with open(split_file, 'r') as f:
                self.video_ids = [line.strip() for line in f if line.strip()]
        else:
            # Use all videos if no split file
            self.video_ids = [
                d.name for d in (self.data_dir).iterdir()
                if d.is_dir() and (d / "frames").exists()
            ]
        
        # Load annotations
        self.annotations = self._load_annotations()
        
        # Create sequence indices
        self.sequences = self._create_sequences()
    
    def _load_annotations(self) -> Dict[str, Dict]:
        """
        Load annotations for all videos.
        
        Returns:
            Dictionary mapping video_id to annotation data
        """
        annotations = {}
        
        for video_id in self.video_ids:
            ann_file = self.data_dir / video_id / "annotations.json"
            if ann_file.exists():
                with open(ann_file, 'r') as f:
                    annotations[video_id] = json.load(f)
        
        return annotations
    
    def _create_sequences(self) -> List[Dict]:
        """
        Create sequence indices from videos.
        
        Returns:
            List of dictionaries with video_id, start_frame, label
        """
        sequences = []
        
        for video_id in self.video_ids:
            if video_id not in self.annotations:
                continue
            
            ann = self.annotations[video_id]
            frames_dir = self.data_dir / video_id / "frames"
            
            if not frames_dir.exists():
                continue
            
            # Count frames
            num_frames = len(list(frames_dir.glob("*.jpg")))
            
            if num_frames < self.sequence_length:
                continue
            
            # Get task segments
            tasks = ann.get("tasks", [])
            
            for task in tasks:
                task_id = task["id"]
                start_frame = task["start_frame"]
                end_frame = task["end_frame"]
                
                # Create sequences for this task
                for seq_start in range(
                    max(0, start_frame - self.sequence_length + 1),
                    min(end_frame, num_frames - self.sequence_length + 1)
                ):
                    sequences.append({
                        "video_id": video_id,
                        "start_frame": seq_start,
                        "task_id": task_id,
                        "label": self._task_to_label(task_id)
                    })
        
        return sequences
    
    def _task_to_label(self, task_id: str) -> int:
        """
        Convert task ID to label index.
        
        Args:
            task_id: Task identifier (e.g., "TASK-01")
        
        Returns:
            Integer label (0-5)
        """
        task_map = {
            "TASK-01": 0,  # Pre-cleaning
            "TASK-02": 1,  # Stripping
            "TASK-03": 2,  # Machine attachment
            "TASK-04": 3,  # Milking (active)
            "TASK-05": 4,  # Detachment
            "TASK-06": 5,  # Post-dip
        }
        return task_map.get(task_id, -1)
    
    def __len__(self) -> int:
        """Return the number of sequences."""
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, int]:
        """
        Get a sequence and its label.
        
        Args:
            idx: Index of the sequence
        
        Returns:
            Tuple of (features, label)
        """
        seq_info = self.sequences[idx]
        video_id = seq_info["video_id"]
        start_frame = seq_info["start_frame"]
        label = seq_info["label"]
        
        # Load frames
        frames = []
        frames_dir = self.data_dir / video_id / "frames"
        
        for i in range(self.sequence_length):
            frame_path = frames_dir / f"{start_frame + i:04d}.jpg"
            if frame_path.exists():
                frame = cv2.imread(str(frame_path))
                if self.transform:
                    frame = self.transform(image=frame)["image"]
                frames.append(frame)
            else:
                # Use zeros if frame missing
                frames.append(np.zeros((640, 640, 3), dtype=np.uint8))
        
        # Extract features if feature extractor provided
        if self.feature_extractor is not None:
            features = self.feature_extractor.extract_sequence_features(frames)
        else:
            # Return raw frames (for models that process frames directly)
            features = np.array(frames)
        
        # Convert to tensors
        features_tensor = torch.FloatTensor(features)
        label_tensor = torch.LongTensor([label])[0]
        
        return features_tensor, label_tensor
    
    def get_class_weights(self) -> torch.Tensor:
        """
        Calculate class weights for imbalanced datasets.
        
        Returns:
            Tensor of class weights
        """
        label_counts = np.zeros(6)
        
        for seq in self.sequences:
            label = seq["label"]
            if label >= 0:
                label_counts[label] += 1
        
        # Inverse frequency
        total = label_counts.sum()
        weights = total / (label_counts + 1e-6)
        
        # Normalize
        weights = weights / weights.sum() * len(weights)
        
        return torch.FloatTensor(weights)


def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    sequence_length: int = 30,
    feature_extractor=None,
    num_workers: int = 4
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train, validation, and test dataloaders.
    
    Args:
        data_dir: Path to processed data directory
        batch_size: Batch size
        sequence_length: Number of frames per sequence
        feature_extractor: YOLOFeatureExtractor instance
        num_workers: Number of workers for data loading
    
    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    train_dataset = MilkingSequenceDataset(
        data_dir=data_dir,
        split="train",
        sequence_length=sequence_length,
        feature_extractor=feature_extractor
    )
    
    val_dataset = MilkingSequenceDataset(
        data_dir=data_dir,
        split="val",
        sequence_length=sequence_length,
        feature_extractor=feature_extractor
    )
    
    test_dataset = MilkingSequenceDataset(
        data_dir=data_dir,
        split="test",
        sequence_length=sequence_length,
        feature_extractor=feature_extractor
    )
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return train_loader, val_loader, test_loader
