"""
Module 120: Primary Traffic Predictor — LSTM Architecture
Forecasts near-future network QoS degradation S_hat(t+Delta) = [L, J, P_L, U]
from the rolling history window [S(t-k), ..., S(t)] maintained by the Digital Twin.
"""

import torch
import torch.nn as nn
from typing import Tuple

class LSTMTrafficPredictor(nn.Module):
    def __init__(
        self,
        input_dim: int = 4,
        hidden_dim: int = 64,
        num_layers: int = 2,
        output_dim: int = 4,
        dropout: float = 0.1
    ):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.output_dim = output_dim

        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0
        )

        self.head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, output_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (batch_size, sequence_length_k, input_dim)
        Returns:
            Forecasted state vector of shape (batch_size, output_dim)
        """
        # lstm_out: (B, k, hidden_dim)
        lstm_out, _ = self.lstm(x)
        # Take representation at last time step
        last_step_repr = lstm_out[:, -1, :]
        # Predict future state
        pred = self.head(last_step_repr)
        return pred
