"""
Unit tests for CogniNet-6G Phase 1 Scaffolding and Environment.
Validates repository structure, YAML configurations, and mathematical parameters.
"""

import os
import yaml
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def test_directory_structure():
    """Verify all required directories exist in the repository."""
    required_dirs = [
        "configs/simulation",
        "configs/models",
        "configs/training",
        "configs/experiments",
        "configs/baselines",
        "cogninet/telemetry",
        "cogninet/digital_twin",
        "cogninet/prediction",
        "cogninet/semantic",
        "cogninet/scheduler",
        "cogninet/safety",
        "cogninet/orchestration",
        "cogninet/edge_service",
        "cogninet/monitoring",
        "cogninet/feedback",
        "sim/ros2_ws",
        "sim/ns3",
        "datasets/raw",
        "datasets/processed",
        "datasets/metadata",
        "training",
        "baselines",
        "experiments/scenarios",
        "experiments/configs",
        "experiments/runners",
        "evaluation",
        "visualization",
        "results/raw",
        "results/processed",
        "results/tables",
        "results/figures",
        "reports/experiment_log",
        "reports/research_notes",
        "tests",
        "scripts"
    ]
    for d in required_dirs:
        full_path = os.path.join(REPO_ROOT, d)
        assert os.path.isdir(full_path), f"Missing required directory: {d}"

def test_governance_files():
    """Verify all essential governance and documentation files exist."""
    required_files = [
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "CONTRIBUTIONS.md",
        "METHODOLOGY.md",
        "LIMITATIONS.md",
        "literature_matrix.yaml",
        "requirements.txt",
        "pyproject.toml",
        "docker-compose.yml",
        "reports/research_decision_log.md"
    ]
    for f in required_files:
        full_path = os.path.join(REPO_ROOT, f)
        assert os.path.isfile(full_path), f"Missing required file: {f}"

def test_sim_config_parameters():
    """Validate canonical parameters in sim_config.yaml."""
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    assert os.path.isfile(cfg_path), "sim_config.yaml does not exist"
    
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        
    # Check fleet
    assert cfg["fleet"]["num_robots"] >= 1
    assert len(cfg["fleet"]["robot_ids"]) == cfg["fleet"]["num_robots"]
    
    # Check timing
    assert cfg["timing"]["delta_t"] > 0
    assert cfg["timing"]["forecast_horizon"] > 0
    assert cfg["timing"]["history_window_k"] >= 1
    
    # Check capacity
    assert cfg["network"]["r_max_mbps"] > 0
    
    # Check safety parameters
    assert 0.0 < cfg["safety"]["w_crit"] <= 1.0
    assert cfg["safety"]["d_max_ms"] > 0
    assert cfg["safety"]["enforce_strict"] is True
    
    # Check reward weights sum and bounds
    weights = cfg["reward_weights"]
    for w in ["alpha", "beta", "eta", "zeta", "lambda_reconfig"]:
        assert w in weights
        assert weights[w] > 0.0

def test_baseline_config_parameters():
    """Validate baseline parameters in baselines.yaml."""
    cfg_path = os.path.join(REPO_ROOT, "configs", "baselines", "baselines.yaml")
    assert os.path.isfile(cfg_path), "baselines.yaml does not exist"
    
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
        
    assert "static_slicing" in cfg
    assert "reactive_threshold" in cfg
    assert cfg["reactive_threshold"]["thresholds"]["latency_trigger_ms"] > 0
    assert cfg["reactive_threshold"]["thresholds"]["packet_loss_trigger"] > 0
