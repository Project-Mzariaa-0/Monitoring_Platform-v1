"""
Training script for the hybrid YOLO + LSTM model.
"""

import os
import sys
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
from tqdm import tqdm
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ModelConfig, load_config
from temporal.lstm_model import MilkingActionLSTM
from temporal.preextracted_dataset import create_dataloaders


class Trainer:
    """
    Training manager for the LSTM model.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the trainer.
        
        Args:
            config: Model configuration
        """
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize model
        self.model = MilkingActionLSTM(
            input_size=config.lstm.input_size,
            hidden_size=config.lstm.hidden_size,
            num_layers=config.lstm.num_layers,
            num_classes=config.lstm.num_classes,
            dropout=config.lstm.dropout,
            bidirectional=config.lstm.bidirectional
        ).to(self.device)
        
        # Loss function with class weights
        self.criterion = nn.CrossEntropyLoss()
        
        # Optimizer
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=config.training.learning_rate,
            weight_decay=config.training.weight_decay
        )
        
        # Scheduler
        self.scheduler = optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=config.training.epochs
        )
        
        # Tracking
        self.train_losses = []
        self.val_losses = []
        self.train_accs = []
        self.val_accs = []
        self.best_val_acc = 0.0
        
        # Create directories
        os.makedirs(config.models_dir, exist_ok=True)
        os.makedirs(config.checkpoints_dir, exist_ok=True)
    
    def train_epoch(self, train_loader: DataLoader) -> Tuple[float, float]:
        """
        Train for one epoch.
        
        Args:
            train_loader: Training data loader
        
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.train()
        total_loss = 0.0
        correct = 0
        total = 0
        
        pbar = tqdm(train_loader, desc="Training")
        
        for batch_idx, (features, labels) in enumerate(pbar):
            features = features.to(self.device)
            labels = labels.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs, _ = self.model(features)
            loss = self.criterion(outputs, labels)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            
            # Track metrics
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Update progress bar
            pbar.set_postfix({
                'loss': loss.item(),
                'acc': 100. * correct / total
            })
        
        avg_loss = total_loss / len(train_loader)
        accuracy = 100. * correct / total
        
        return avg_loss, accuracy  
    
    def validate(self, val_loader: DataLoader) -> Tuple[float, float]:
        """
        Validate the model.
        
        Args:
            val_loader: Validation data loader
        
        Returns:
            Tuple of (average_loss, accuracy)
        """
        self.model.eval()
        total_loss = 0.0
        correct = 0
        total = 0
        
        with torch.no_grad():
            for features, labels in val_loader:
                features = features.to(self.device)
                labels = labels.to(self.device)
                
                outputs, _ = self.model(features)
                loss = self.criterion(outputs, labels)
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        avg_loss = total_loss / len(val_loader)
        accuracy = 100. * correct / total
        
        return avg_loss, accuracy
    
    def train(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = None
    ):
        """
        Full training loop.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            epochs: Number of epochs (overrides config)
        """
        if epochs is None:
            epochs = self.config.training.epochs
        
        self.logger.info(f"Starting training for {epochs} epochs")
        self.logger.info(f"Device: {self.device}")
        self.logger.info(f"Model parameters: {sum(p.numel() for p in self.model.parameters()):,}")
        
        patience_counter = 0
        
        for epoch in range(epochs):
            self.logger.info(f"\nEpoch {epoch+1}/{epochs}")
            self.logger.info("-" * 40)
            
            # Train
            train_loss, train_acc = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            self.train_accs.append(train_acc)
            
            # Validate
            val_loss, val_acc = self.validate(val_loader)
            self.val_losses.append(val_loss)
            self.val_accs.append(val_acc)
            
            # Update scheduler
            self.scheduler.step()
            
            # Log metrics
            self.logger.info(f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}%")
            self.logger.info(f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}%")
            
            # Save best model
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                self.save_checkpoint("best_model.pt")
                self.logger.info(f"New best model saved! Val Acc: {val_acc:.2f}%")
                patience_counter = 0
            else:
                patience_counter += 1
            
            # Early stopping
            if (self.config.training.early_stopping_enabled and
                patience_counter >= self.config.training.early_stopping_patience):
                self.logger.info(f"Early stopping at epoch {epoch+1}")
                break
            
            # Save periodic checkpoint
            if (epoch + 1) % 10 == 0:
                self.save_checkpoint(f"checkpoint_epoch_{epoch+1}.pt")
        
        # Save final model
        self.save_checkpoint("final_model.pt")
        self.save_training_history()
        
        self.logger.info(f"\nTraining complete! Best Val Acc: {self.best_val_acc:.2f}%")
    
    def save_checkpoint(self, filename: str):
        """
        Save model checkpoint.
        
        Args:
            filename: Checkpoint filename
        """
        checkpoint_path = Path(self.config.checkpoints_dir) / filename
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_acc': self.best_val_acc,
            'config': {
                'input_size': self.config.lstm.input_size,
                'hidden_size': self.config.lstm.hidden_size,
                'num_layers': self.config.lstm.num_layers,
                'num_classes': self.config.lstm.num_classes,
                'dropout': self.config.lstm.dropout,
                'bidirectional': self.config.lstm.bidirectional,
            }
        }, checkpoint_path)
    
    def save_training_history(self):
        """Save training history to JSON."""
        history = {
            'train_losses': self.train_losses,
            'val_losses': self.val_losses,
            'train_accs': self.train_accs,
            'val_accs': self.val_accs,
            'best_val_acc': self.best_val_acc
        }
        
        history_path = Path(self.config.models_dir) / "training_history.json"
        with open(history_path, 'w') as f:
            json.dump(history, f, indent=2)
    
    def load_checkpoint(self, filename: str):
        """
        Load model checkpoint.
        
        Args:
            filename: Checkpoint filename
        """
        checkpoint_path = Path(self.config.checkpoints_dir) / filename
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
        
        checkpoint = torch.load(checkpoint_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.best_val_acc = checkpoint['best_val_acc']
        
        self.logger.info(f"Loaded checkpoint: {filename}")


def main():
    """Main training function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train hybrid YOLO + LSTM model")
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Path to config file")
    parser.add_argument("--epochs", type=int, default=None,
                        help="Number of epochs (overrides config)")
    parser.add_argument("--batch-size", type=int, default=None,
                        help="Batch size (overrides config)")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Path to processed data directory")
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    
    # Override config with CLI args
    if args.epochs:
        config.training.epochs = args.epochs
    if args.batch_size:
        config.training.batch_size = args.batch_size
    if args.data_dir:
        config.data.processed_dir = args.data_dir
    
    # Create dataloaders
    print("Loading data...")
    train_loader, val_loader, test_loader = create_dataloaders(
        data_dir=config.data.processed_dir,
        batch_size=config.training.batch_size,
        sequence_length=config.lstm.sequence_length,
        feature_extractor=None  # Features should be pre-extracted
    )
    
    print(f"Train: {len(train_loader.dataset)} sequences")
    print(f"Val: {len(val_loader.dataset)} sequences")
    print(f"Test: {len(test_loader.dataset)} sequences")
    
    # Train
    trainer = Trainer(config)
    trainer.train(train_loader, val_loader)
    
    # Evaluate on test set
    print("\nEvaluating on test set...")
    test_loss, test_acc = trainer.validate(test_loader)
    print(f"Test Loss: {test_loss:.4f} | Test Acc: {test_acc:.2f}%")


if __name__ == "__main__":
    main()
