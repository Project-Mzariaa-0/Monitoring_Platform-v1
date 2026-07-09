"""
Utility functions for visualization and metrics.
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple
import json
from pathlib import Path


def plot_training_history(history_path: str, output_path: str = None):
    """
    Plot training history from JSON file.
    
    Args:
        history_path: Path to training_history.json
        output_path: Path to save plot (optional)
    """
    with open(history_path, 'r') as f:
        history = json.load(f)
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # Plot losses
    axes[0].plot(history['train_losses'], label='Train Loss')
    axes[0].plot(history['val_losses'], label='Val Loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].set_title('Training and Validation Loss')
    axes[0].legend()
    axes[0].grid(True)
    
    # Plot accuracies
    axes[1].plot(history['train_accs'], label='Train Acc')
    axes[1].plot(history['val_accs'], label='Val Acc')
    axes[1].set_xlabel('Epoch')
    axes[1].set_ylabel('Accuracy (%)')
    axes[1].set_title('Training and Validation Accuracy')
    axes[1].legend()
    axes[1].grid(True)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def plot_confusion_matrix(
    y_true: List[int],
    y_pred: List[int],
    class_names: List[str],
    output_path: str = None
):
    """
    Plot confusion matrix.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        class_names: List of class names
        output_path: Path to save plot (optional)
    """
    from sklearn.metrics import confusion_matrix
    import seaborn as sns
    
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=class_names,
        yticklabels=class_names
    )
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close()


def calculate_metrics(
    y_true: List[int],
    y_pred: List[int],
    num_classes: int = 6
) -> Dict[str, float]:
    """
    Calculate classification metrics.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        num_classes: Number of classes
    
    Returns:
        Dictionary of metrics
    """
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score
    )
    
    metrics = {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_macro": precision_score(y_true, y_pred, average='macro', zero_division=0),
        "recall_macro": recall_score(y_true, y_pred, average='macro', zero_division=0),
        "f1_macro": f1_score(y_true, y_pred, average='macro', zero_division=0),
    }
    
    # Per-class metrics
    precision_per_class = precision_score(y_true, y_pred, average=None, zero_division=0)
    recall_per_class = recall_score(y_true, y_pred, average=None, zero_division=0)
    f1_per_class = f1_score(y_true, y_pred, average=None, zero_division=0)
    
    for i in range(num_classes):
        metrics[f"precision_class_{i}"] = precision_per_class[i] if i < len(precision_per_class) else 0
        metrics[f"recall_class_{i}"] = recall_per_class[i] if i < len(recall_per_class) else 0
        metrics[f"f1_class_{i}"] = f1_per_class[i] if i < len(f1_per_class) else 0
    
    return metrics
