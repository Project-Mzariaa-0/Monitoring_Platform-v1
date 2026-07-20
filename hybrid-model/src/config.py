"""
Configuration management for the hybrid model.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import yaml


@dataclass
class YOLOConfig:
    """YOLO detector configuration."""
    model: str = "yolov8n.pt"
    confidence: float = 0.05
    device: str = "auto"
    input_size: int = 640
    
    # Classes to detect (COCO class indices)
    # 0: person, 15: cat, 16: dog, etc.
    target_classes: List[int] = field(default_factory=lambda: [0])  # Only person


@dataclass
class LSTMConfig:
    """LSTM model configuration."""
    input_size: int = 640  # Multimodal: pose(512) + objects(128)
    hidden_size: int = 128
    num_layers: int = 1
    bidirectional: bool = False
    dropout: float = 0.7
    sequence_length: int = 30  # frames (6 seconds at 5 FPS)
    num_classes: int = 6  # milking tasks
    
    # Task labels
    task_labels: List[str] = field(default_factory=lambda: [
        "TASK-01",  # Pre-cleaning
        "TASK-02",  # Stripping
        "TASK-03",  # Machine attachment
        "TASK-04",  # Milking (active)
        "TASK-05",  # Detachment
        "TASK-06",  # Post-dip
    ])


@dataclass
class TrainingConfig:
    """Training configuration."""
    epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    weight_decay: float = 0.0001
    
    # Optimizer
    optimizer: str = "adam"
    scheduler: str = "cosine"
    
    # Data splits
    train_split: float = 0.8
    val_split: float = 0.1
    test_split: float = 0.1
    
    # Early stopping
    early_stopping_enabled: bool = True
    early_stopping_patience: int = 10
    early_stopping_min_delta: float = 0.001


@dataclass
class DataConfig:
    """Data configuration."""
    raw_dir: str = "data/raw"
    processed_dir: str = "data/processed"
    splits_dir: str = "data/splits"
    
    # Video settings
    video_format: str = "mp4"
    target_fps: int = 5
    frame_size: List[int] = field(default_factory=lambda: [640, 640])


@dataclass
class InferenceConfig:
    """Inference configuration."""
    source: str = "rtsp://camera-ip/stream"
    show_display: bool = True
    save_output: bool = False
    
    # Thresholds
    yolo_threshold: float = 0.3
    lstm_threshold: float = 0.5
    
    # Performance
    max_latency_ms: int = 250
    target_fps: int = 4


@dataclass
class StationConfig:
    """Station location configuration."""
    dip_station: List[float] = field(default_factory=lambda: [0.1, 0.7, 0.2, 0.3])


@dataclass
class DomainConfig:
    """Domain-specific configuration."""
    stations: StationConfig = field(default_factory=StationConfig)
    max_persons: int = 2
    camera_resolution: List[int] = field(default_factory=lambda: [1248, 576])


@dataclass
class ModelConfig:
    """Main model configuration."""
    yolo: YOLOConfig = field(default_factory=YOLOConfig)
    lstm: LSTMConfig = field(default_factory=LSTMConfig)
    training: TrainingConfig = field(default_factory=TrainingConfig)
    data: DataConfig = field(default_factory=DataConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    domain: DomainConfig = field(default_factory=DomainConfig)
    
    # Paths
    models_dir: str = "models"
    logs_dir: str = "logs"
    checkpoints_dir: str = "models/checkpoints"


def load_config(config_path: Optional[str] = None) -> ModelConfig:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config file. If None, uses default.
    
    Returns:
        ModelConfig instance
    """
    config = ModelConfig()
    
    if config_path and os.path.exists(config_path):
        with open(config_path, 'r') as f:
            yaml_config = yaml.safe_load(f)
        
        # Update config from YAML
        if 'model' in yaml_config:
            if 'yolo' in yaml_config['model']:
                for k, v in yaml_config['model']['yolo'].items():
                    if hasattr(config.yolo, k):
                        setattr(config.yolo, k, v)
            
            if 'lstm' in yaml_config['model']:
                for k, v in yaml_config['model']['lstm'].items():
                    if hasattr(config.lstm, k):
                        setattr(config.lstm, k, v)
        
        if 'training' in yaml_config:
            for k, v in yaml_config['training'].items():
                if hasattr(config.training, k):
                    setattr(config.training, k, v)
        
        if 'data' in yaml_config:
            for k, v in yaml_config['data'].items():
                if hasattr(config.data, k):
                    setattr(config.data, k, v)
        
        if 'inference' in yaml_config:
            for k, v in yaml_config['inference'].items():
                if hasattr(config.inference, k):
                    setattr(config.inference, k, v)
    
    return config


def get_device(config: ModelConfig) -> str:
    """
    Get the appropriate device for inference.
    
    Args:
        config: Model configuration
    
    Returns:
        Device string ("cpu", "cuda:0", etc.)
    """
    import torch
    
    if config.yolo.device == "auto":
        if torch.cuda.is_available():
            return "cuda:0"
        return "cpu"
    
    return config.yolo.device
