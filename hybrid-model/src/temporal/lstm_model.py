"""
LSTM temporal model for milking action recognition.
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional


class MilkingActionLSTM(nn.Module):
    """
    LSTM model for classifying milking actions from frame sequences.
    
    This model takes a sequence of YOLO features and classifies
    which milking task is being performed.
    """
    
    def __init__(
        self,
        input_size: int = 256,
        hidden_size: int = 256,
        num_layers: int = 2,
        num_classes: int = 6,
        dropout: float = 0.3,
        bidirectional: bool = True
    ):
        """
        Initialize the LSTM model.
        
        Args:
            input_size: Size of input features (from YOLO)
            hidden_size: Size of LSTM hidden state
            num_layers: Number of LSTM layers
            num_classes: Number of output classes (milking tasks)
            dropout: Dropout rate
            bidirectional: Use bidirectional LSTM
        """
        super(MilkingActionLSTM, self).__init__()
        
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.bidirectional = bidirectional
        
        # Feature extractor (per frame)
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # LSTM temporal model
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )
        
        # Output size depends on bidirectional
        lstm_output_size = hidden_size * 2 if bidirectional else hidden_size
        
        # Task classifier
        self.classifier = nn.Sequential(
            nn.Linear(lstm_output_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(64, num_classes)
        )
        
        # Attention mechanism (optional, for interpretability)
        self.attention = nn.Sequential(
            nn.Linear(lstm_output_size, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
            nn.Softmax(dim=1)
        )
    
    def forward(
        self,
        x: torch.Tensor,
        return_attention: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Forward pass through the model.
        
        Args:
            x: Input tensor of shape (batch, sequence_length, input_size)
            return_attention: If True, return attention weights
        
        Returns:
            Tuple of (output, attention_weights)
            - output: (batch, num_classes) logits
            - attention_weights: (batch, sequence_length, 1) if return_attention else None
        """
        batch_size, seq_len, _ = x.shape
        
        # Extract features from each frame
        x = x.view(batch_size * seq_len, self.input_size)
        x = self.feature_extractor(x)
        x = x.view(batch_size, seq_len, 128)
        
        # LSTM processing
        lstm_out, (h_n, c_n) = self.lstm(x)
        # lstm_out shape: (batch, seq_len, hidden_size * num_directions)
        
        # Attention mechanism
        attention_weights = self.attention(lstm_out)
        # attention_weights shape: (batch, seq_len, 1)
        
        # Weighted sum using attention
        context = torch.sum(attention_weights * lstm_out, dim=1)
        # context shape: (batch, hidden_size * num_directions)
        
        # Classify
        output = self.classifier(context)
        # output shape: (batch, num_classes)
        
        if return_attention:
            return output, attention_weights
        
        return output, None
    
    def predict(
        self,
        x: torch.Tensor,
        threshold: float = 0.5
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Make predictions with confidence scores.
        
        Args:
            x: Input tensor of shape (batch, sequence_length, input_size)
            threshold: Confidence threshold for predictions
        
        Returns:
            Tuple of (predictions, confidences)
        """
        with torch.no_grad():
            output, _ = self.forward(x)
            probabilities = torch.softmax(output, dim=1)
            predictions = torch.argmax(probabilities, dim=1)
            confidences = torch.max(probabilities, dim=1).values
        
        return predictions, confidences
    
    def get_attention_weights(
        self,
        x: torch.Tensor
    ) -> torch.Tensor:
        """
        Get attention weights for interpretability.
        
        Args:
            x: Input tensor of shape (batch, sequence_length, input_size)
        
        Returns:
            Attention weights of shape (batch, sequence_length, 1)
        """
        with torch.no_grad():
            _, attention_weights = self.forward(x, return_attention=True)
        
        return attention_weights


class TemporalConvLSTM(nn.Module):
    """
    Alternative model using Conv1D + LSTM for better temporal feature extraction.
    """
    
    def __init__(
        self,
        input_size: int = 256,
        hidden_size: int = 256,
        num_layers: int = 2,
        num_classes: int = 6,
        dropout: float = 0.3
    ):
        super(TemporalConvLSTM, self).__init__()
        
        # Temporal convolution
        self.conv1d = nn.Sequential(
            nn.Conv1d(input_size, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Conv1d(128, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # LSTM
        self.lstm = nn.LSTM(
            input_size=128,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, seq_len, input_size)
        
        # Conv1d expects (batch, channels, length)
        x = x.permute(0, 2, 1)
        x = self.conv1d(x)
        
        # Back to (batch, seq_len, features)
        x = x.permute(0, 2, 1)
        
        # LSTM
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use last hidden state
        final_hidden = torch.cat([h_n[-2], h_n[-1]], dim=1)
        
        # Classify
        output = self.classifier(final_hidden)
        
        return output
