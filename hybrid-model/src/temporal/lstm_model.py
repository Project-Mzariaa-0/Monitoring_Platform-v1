"""
LSTM temporal model for milking action recognition.
"""

import torch
import torch.nn as nn
from typing import Tuple, Optional


class MilkingActionLSTM(nn.Module):
    """
    Lightweight LSTM model for classifying milking actions from frame sequences.

    ~51K params (suitable for ~180 training sequences).
    """

    def __init__(
        self,
        input_size: int = 512,
        hidden_size: int = 64,
        num_layers: int = 1,
        num_classes: int = 6,
        dropout: float = 0.5,
        bidirectional: bool = False
    ):
        super(MilkingActionLSTM, self).__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_classes = num_classes
        self.bidirectional = bidirectional

        # Per-frame feature extractor
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_size, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # LSTM temporal model
        self.lstm = nn.LSTM(
            input_size=64,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=bidirectional
        )

        lstm_output_size = hidden_size * 2 if bidirectional else hidden_size

        # Attention mechanism
        self.attention = nn.Sequential(
            nn.Linear(lstm_output_size, 32),
            nn.Tanh(),
            nn.Linear(32, 1),
            nn.Softmax(dim=1)
        )

        # Task classifier
        self.classifier = nn.Sequential(
            nn.Linear(lstm_output_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, num_classes)
        )

    def forward(
        self,
        x: torch.Tensor,
        return_attention: bool = False
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor]]:
        """
        Args:
            x: (batch, sequence_length, input_size)
            return_attention: If True, return attention weights

        Returns:
            (output, attention_weights)
            - output: (batch, num_classes) logits
            - attention_weights: (batch, sequence_length, 1) or None
        """
        batch_size, seq_len, _ = x.shape

        # Extract features from each frame
        x = x.view(batch_size * seq_len, self.input_size)
        x = self.feature_extractor(x)
        x = x.view(batch_size, seq_len, 64)

        # LSTM processing
        lstm_out, _ = self.lstm(x)

        # Attention-weighted pooling
        attention_weights = self.attention(lstm_out)
        context = torch.sum(attention_weights * lstm_out, dim=1)

        # Classify
        output = self.classifier(context)

        if return_attention:
            return output, attention_weights

        return output, None

    def predict(
        self,
        x: torch.Tensor,
        threshold: float = 0.5
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        with torch.no_grad():
            output, _ = self.forward(x)
            probabilities = torch.softmax(output, dim=1)
            predictions = torch.argmax(probabilities, dim=1)
            confidences = torch.max(probabilities, dim=1).values
        return predictions, confidences

    def get_attention_weights(self, x: torch.Tensor) -> torch.Tensor:
        with torch.no_grad():
            _, attention_weights = self.forward(x, return_attention=True)
        return attention_weights
