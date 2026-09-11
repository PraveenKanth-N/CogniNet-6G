"""
Unit and Integration Tests for Closed-Loop Orchestration (Algorithm 1 / Phase 8)
Tests ActionHandler (Module 150) and ClosedLoopOrchestrator (Module 170).
"""

import os
import pytest
import yaml
import numpy as np

from cogninet.orchestration.action_handler import ActionHandler
from cogninet.feedback.loop import ClosedLoopOrchestrator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import Scenario

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

@pytest.fixture
def sim_config():
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_action_handler_validation(sim_config):
    handler = ActionHandler(r_max_mbps=100.0)
    net = Ns3NetworkModel(sim_config, random_seed=42)

    # 1. Valid allocation
    valid_alloc = {f"r{i+1:02d}": 10.0 for i in range(10)}
    rec = handler.dispatch(net, valid_alloc, timestamp=0.0)
    assert rec["total_allocated_mbps"] == 100.0
    assert rec["reconfiguration_cost"] == 0.0

    # 2. Exceeding R_max should raise ValueError
    invalid_alloc_over = {f"r{i+1:02d}": 15.0 for i in range(10)}  # 150 Mbps
    with pytest.raises(ValueError, match="exceeds R_max"):
        handler.dispatch(net, invalid_alloc_over, timestamp=0.5)

    # 3. Negative allocation should raise ValueError
    invalid_alloc_neg = {f"r{i+1:02d}": 10.0 for i in range(9)}
    invalid_alloc_neg["r10"] = -5.0
    with pytest.raises(ValueError, match="Negative bandwidth"):
        handler.dispatch(net, invalid_alloc_neg, timestamp=1.0)

    # 4. Reconfiguration cost calculation
    prev = {f"r{i+1:02d}": 10.0 for i in range(10)}
    curr = {f"r{i+1:02d}": 10.0 for i in range(10)}
    curr["r01"] = 20.0
    curr["r02"] = 0.0
    cost = handler.compute_reconfiguration_cost(curr, prev)
    expected_norm = np.sqrt((10.0**2) + ((-10.0)**2)) / 100.0
    assert np.isclose(cost, expected_norm, atol=1e-5)

def test_closed_loop_orchestrator_execution(sim_config):
    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    model_paths = {
        "predictor": os.path.join(models_dir, "lstm_predictor.pt"),
        "semantic": os.path.join(models_dir, "semantic_classifier.pt"),
        "ppo": os.path.join(models_dir, "ppo_scheduler.zip")
    }

    orchestrator = ClosedLoopOrchestrator(
        config=sim_config,
        scenario=Scenario.A_NORMAL,
        model_paths=model_paths,
        enable_safety_override=True,
        policy_type="ppo",
        random_seed=42
    )

    # Execute 10 control steps (5.0 seconds simulation time)
    log = orchestrator.run_simulation(duration_s=5.0)
    assert len(log) == 10

    first_step = log[0]
    assert "step" in first_step
    assert "reward" in first_step
    assert "state" in first_step
    assert "predicted_state" in first_step
    assert "timing_ms" in first_step
    assert "allocations" in first_step

    # Verify real-time constraint: mean loop latency <= 50 ms and steady-state <= 50 ms
    mean_loop_ms = sum(record["timing_ms"]["total_loop_ms"] for record in log) / len(log)
    assert mean_loop_ms < 50.0, f"Mean loop latency {mean_loop_ms} exceeded 50ms"
    for record in log[1:]:
        assert record["timing_ms"]["total_loop_ms"] < 50.0, f"Steady-state latency {record['timing_ms']['total_loop_ms']} exceeded 50ms"

def test_closed_loop_safety_override_guarantee(sim_config):
    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    model_paths = {
        "predictor": os.path.join(models_dir, "lstm_predictor.pt"),
        "semantic": os.path.join(models_dir, "semantic_classifier.pt")
    }

    # Use congestion burst scenario where urgent packets appear
    orchestrator = ClosedLoopOrchestrator(
        config=sim_config,
        scenario=Scenario.B_CONGESTION_BURST,
        model_paths=model_paths,
        enable_safety_override=True,
        policy_type="ppo",
        random_seed=42
    )

    log = orchestrator.run_simulation(duration_s=10.0)
    assert len(log) == 20

    # Ensure any robot flagged with critical weight (>= 0.85) received >= 15 Mbps
    for record in log:
        weights = record["weights"]
        allocations = record["allocations"]
        for rid, w in weights.items():
            if w >= 0.85:
                assert allocations[rid] >= 14.99, f"Critical robot {rid} (w={w}) received insufficient {allocations[rid]} Mbps"
