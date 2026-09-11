"""
Unit and Adversarial Safety Tests for Phase 7: RL Scheduler & Safety Override
Validates Gymnasium environment, reward computation, and executes adversarial tests
proving the deterministic safety override strictly protects critical traffic.
"""

import os
import yaml
import pytest
import numpy as np
from cogninet.safety.safety_override import SafetyConstraintLayer
from cogninet.scheduler.reward import RewardCalculator
from cogninet.scheduler.gym_env import CogniNetSlicingEnv
from experiments.scenarios.traffic_generator import Scenario

@pytest.fixture
def sim_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_reward_calculator():
    calc = RewardCalculator(alpha=0.35, beta=0.25, eta=0.20, zeta=0.10, lambda_reconfig=0.10)

    # 1. Excellent state: low latency, 0 loss, SLA met, good utilization, no reconfig
    state_good = [5.0, 1.0, 0.0, 0.8]
    a_prev = {"r01": 10.0, "r02": 10.0}
    a_curr = {"r01": 10.0, "r02": 10.0}
    rw_good = calc.compute(state_good, sla_satisfied=True, current_action=a_curr, previous_action=a_prev)

    assert rw_good.sla_reward == pytest.approx(0.20)
    assert rw_good.loss_penalty == pytest.approx(0.0)
    assert rw_good.reconfiguration_penalty == pytest.approx(0.0)
    assert rw_good.total_reward > 0.0

    # 2. Heavy thrashing & degradation: high latency, 10% loss, SLA failed, drastic action change
    state_bad = [90.0, 10.0, 0.10, 0.2]
    a_thrash = {"r01": 90.0, "r02": 10.0}
    rw_bad = calc.compute(state_bad, sla_satisfied=False, current_action=a_thrash, previous_action=a_prev)

    assert rw_bad.sla_reward == 0.0
    assert rw_bad.loss_penalty < 0.0
    assert rw_bad.reconfiguration_penalty < 0.0
    assert rw_bad.total_reward < rw_good.total_reward

def test_gym_environment_lifecycle(sim_config):
    env = CogniNetSlicingEnv(config=sim_config, scenario=Scenario.A_NORMAL, max_steps=10, enable_safety_override=True)
    obs, info = env.reset(seed=42)

    assert obs.shape == (29,)
    assert not np.isnan(obs).any()

    # Step random action
    action = env.action_space.sample()
    obs_next, r, term, trunc, step_info = env.step(action)

    assert obs_next.shape == (29,)
    assert isinstance(r, float)
    assert "reward_breakdown" in step_info
    assert sum(step_info["allocations"].values()) <= 100.001

def test_adversarial_safety_override_single_critical():
    """
    Adversarial Test 1:
    The PPO agent is intentionally adversarial and outputs 0.0 Mbps to robot r01
    even though r01 has an emergency stop command (w_01 >= w_crit).
    The safety layer MUST override the allocation to at least min_critical_bandwidth_mbps.
    """
    safety = SafetyConstraintLayer(r_max_mbps=100.0, w_crit=0.85, min_critical_bandwidth_mbps=15.0)

    # Adversarial candidate action: 0 Mbps to r01, 100 Mbps to r02
    cand = {"r01": 0.0, "r02": 100.0}
    # Semantic weights: r01 is CRITICAL (0.98), r02 is routine (0.15)
    weights = {"r01": 0.98, "r02": 0.15}

    safe_alloc, override_applied = safety.enforce(cand, weights, step=1)

    assert override_applied is True
    assert safe_alloc["r01"] >= 15.0
    assert sum(safe_alloc.values()) <= 100.001
    assert safety.total_violations_blocked == 1

def test_adversarial_safety_override_multiple_simultaneous_emergencies():
    """
    Adversarial Test 2:
    Multiple robots (r01, r02, r03) trigger critical emergency stop signals simultaneously.
    Adversarial policy provides minimal bandwidth (1.0 Mbps each).
    Safety layer MUST guarantee all 3 receive >= 15.0 Mbps while strictly observing R_max <= 100.
    """
    safety = SafetyConstraintLayer(r_max_mbps=100.0, w_crit=0.85, min_critical_bandwidth_mbps=15.0)

    cand = {f"r{i+1:02d}": 10.0 for i in range(10)}
    # Starve critical robots
    cand["r01"] = 1.0
    cand["r02"] = 2.0
    cand["r03"] = 0.5

    weights = {f"r{i+1:02d}": 0.20 for i in range(10)}
    weights["r01"] = 0.95
    weights["r02"] = 0.95
    weights["r03"] = 0.99

    safe_alloc, override_applied = safety.enforce(cand, weights, step=2)

    assert override_applied is True
    assert safe_alloc["r01"] >= 15.0
    assert safe_alloc["r02"] >= 15.0
    assert safe_alloc["r03"] >= 15.0
    assert sum(safe_alloc.values()) <= 100.001
