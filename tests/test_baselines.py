"""
Unit Tests for Phase 4: Baseline Schedulers
Tests Static Slicing, Reactive Threshold, Semantic-Only, and Prediction-Only schedulers.
"""

import pytest
from baselines.static_slicing import StaticSlicingScheduler
from baselines.reactive_threshold import ReactiveThresholdScheduler
from baselines.heuristic_baselines import SemanticOnlyScheduler, PredictionOnlyScheduler

def test_static_slicing():
    sched = StaticSlicingScheduler(r_max_mbps=100.0)
    robots = ["r01", "r02", "r03", "r04", "r05"]
    alloc = sched.allocate(robots)

    assert len(alloc) == 5
    for r in robots:
        assert alloc[r] == pytest.approx(20.0)
    assert sum(alloc.values()) == pytest.approx(100.0)

def test_reactive_threshold():
    sched = ReactiveThresholdScheduler(
        r_max_mbps=100.0,
        latency_threshold_ms=45.0,
        loss_threshold=0.02,
        cooldown_steps=2
    )
    robots = ["r01", "r02", "r03", "r04"]

    # Interval 0: Normal state -> returns uniform allocation
    normal_state = [20.0, 1.0, 0.005, 0.2]
    a0 = sched.allocate(robots, normal_state, flow_metrics={}, step=0)
    assert sum(a0.values()) == pytest.approx(100.0)
    assert sched.reconfiguration_count == 0

    # Interval 1: Degraded state (latency 65ms > 45ms)
    # Robot r01 is congested
    degraded_state = [65.0, 5.0, 0.03, 0.8]
    flow_metrics = {
        "r01": {"tail_p95_latency_ms": 70.0, "packet_loss_ratio": 0.04},
        "r02": {"tail_p95_latency_ms": 15.0, "packet_loss_ratio": 0.001},
        "r03": {"tail_p95_latency_ms": 18.0, "packet_loss_ratio": 0.001},
        "r04": {"tail_p95_latency_ms": 12.0, "packet_loss_ratio": 0.001}
    }
    a1 = sched.allocate(robots, degraded_state, flow_metrics=flow_metrics, step=1)

    # Robot r01 should receive a higher share than healthy robots
    assert a1["r01"] > a1["r02"]
    assert sum(a1.values()) == pytest.approx(100.0)
    assert sched.reconfiguration_count == 1

    # Interval 2: Cooldown active -> should maintain previous allocation even if still degraded
    a2 = sched.allocate(robots, degraded_state, flow_metrics=flow_metrics, step=2)
    assert a2 == a1
    assert sched.reconfiguration_count == 1

def test_semantic_only_scheduler():
    sched = SemanticOnlyScheduler(r_max_mbps=100.0)
    robots = ["r01", "r02"]
    # r01 has emergency stop, r02 has routine telemetry
    msgs = [
        {"robot_id": "r01", "is_critical": True, "urgency": 1.0},
        {"robot_id": "r02", "is_critical": False, "urgency": 0.2}
    ]
    alloc = sched.allocate(robots, msgs)
    assert alloc["r01"] > alloc["r02"]
    assert sum(alloc.values()) == pytest.approx(100.0)

def test_prediction_only_scheduler():
    sched = PredictionOnlyScheduler(r_max_mbps=100.0)
    robots = ["r01", "r02"]
    history_u = {"r01": 0.8, "r02": 0.1}
    alloc = sched.allocate(robots, [20.0, 1.0, 0.01, 0.5], history_u)
    assert alloc["r01"] > alloc["r02"]
    assert sum(alloc.values()) == pytest.approx(100.0)
