"""
Unit Tests for Phase 5: Traffic Prediction Module (120)
Tests LSTM and Transformer tensor shapes, forward inference, and temporal data processing.
"""

import os
import pytest
import torch
import numpy as np
from cogninet.prediction.lstm import LSTMTrafficPredictor
from cogninet.prediction.transformer_baseline import TransformerTrafficPredictor
from training.train_predictor import create_dataset

def test_lstm_predictor_forward():
    batch_size = 8
    seq_len = 10
    input_dim = 4
    output_dim = 4

    model = LSTMTrafficPredictor(input_dim=input_dim, hidden_dim=32, num_layers=2, output_dim=output_dim)
    dummy_input = torch.randn(batch_size, seq_len, input_dim)
    out = model(dummy_input)

    assert out.shape == (batch_size, output_dim)
    assert not torch.isnan(out).any()

def test_transformer_predictor_forward():
    batch_size = 4
    seq_len = 10
    input_dim = 4
    output_dim = 4

    model = TransformerTrafficPredictor(input_dim=input_dim, d_model=32, nhead=2, num_layers=2, output_dim=output_dim)
    dummy_input = torch.randn(batch_size, seq_len, input_dim)
    out = model(dummy_input)

    assert out.shape == (batch_size, output_dim)
    assert not torch.isnan(out).any()

def test_dataset_construction_temporal_integrity():
    raw_dir = os.path.join(os.path.dirname(__file__), "..", "datasets", "raw")
    if not os.path.exists(raw_dir):
        pytest.skip("Raw datasets directory does not exist yet")

    X, Y = create_dataset(raw_dir, k_window=10, forecast_horizon_steps=4)
    assert len(X) > 0
    assert len(Y) == len(X)
    assert X.shape[1:] == (10, 4)
    assert Y.shape[1:] == (4,)
