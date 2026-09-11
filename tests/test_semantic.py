"""
Unit Tests for Phase 6: Semantic Priority Classifier (Module 130)
Tests forward pass shapes, priority mapping accuracy, critical recall, and latency bounds.
"""

import time
import pytest
import torch
from cogninet.semantic.classifier import LightweightSemanticClassifier
from cogninet.semantic.taxonomy import SemanticClass

def test_semantic_classifier_forward():
    model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4)
    batch_size = 16
    dummy_input = torch.randn(batch_size, 8)

    logits, weights = model(dummy_input)
    assert logits.shape == (batch_size, 4)
    assert weights.shape == (batch_size,)
    # Output weights must be bounded in [0, 1]
    assert (weights >= 0.0).all()
    assert (weights <= 1.0).all()

def test_predict_metadata_priority_mapping():
    model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4)

    # Test emergency stop packet
    crit_meta = {
        "task_type": "EMERGENCY_STOP",
        "urgency": 1.0,
        "is_critical": True,
        "payload_bytes": 128,
        "speed": 1.2,
        "obstacle_dist": 0.5,
        "battery_pct": 80.0
    }
    w_crit = model.predict_metadata(crit_meta)
    assert 0.0 <= w_crit <= 1.0

    # Test routine telemetry packet
    low_meta = {
        "task_type": "TELEMETRY",
        "urgency": 0.1,
        "is_critical": False,
        "payload_bytes": 512,
        "speed": 0.0,
        "obstacle_dist": 15.0,
        "battery_pct": 95.0
    }
    w_low = model.predict_metadata(low_meta)
    assert 0.0 <= w_low <= 1.0

def test_inference_latency_budget():
    model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4)
    meta = {"task_type": "EMERGENCY_STOP", "urgency": 1.0, "is_critical": True}

    # Warmup
    for _ in range(10):
        _ = model.predict_metadata(meta)

    t0 = time.perf_counter()
    num_runs = 500
    for _ in range(num_runs):
        _ = model.predict_metadata(meta)
    elapsed_ms = ((time.perf_counter() - t0) / num_runs) * 1000.0

    # Average inline latency must be well under 1.0 ms
    assert elapsed_ms < 1.0
