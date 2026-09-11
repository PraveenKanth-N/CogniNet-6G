"""
Unit Tests for Module 110: Digital Twin Synchronization
Tests state tables, rolling history buffer shape, drift monitoring, staleness detection, and replay logging.
"""

import os
import yaml
import pytest
import numpy as np
from cogninet.telemetry.acquisition import TelemetryAcquisitionModule
from cogninet.digital_twin.sync_manager import DigitalTwinSyncManager
from cogninet.digital_twin.twin_state import RollingHistoryBuffer

@pytest.fixture
def sim_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_rolling_history_buffer():
    buf = RollingHistoryBuffer(capacity=5, feature_dim=4)
    # Empty window should be zero-padded (5, 4)
    w0 = buf.get_window()
    assert w0.shape == (5, 4)
    assert np.all(w0 == 0.0)

    # Add 2 elements -> should pad front with first element
    buf.append([1.0, 2.0, 0.1, 0.5])
    buf.append([1.5, 2.1, 0.2, 0.6])
    w2 = buf.get_window()
    assert w2.shape == (5, 4)
    assert np.allclose(w2[0], [1.0, 2.0, 0.1, 0.5])
    assert np.allclose(w2[-1], [1.5, 2.1, 0.2, 0.6])

    # Fill beyond capacity
    for i in range(10):
        buf.append([float(i), 0.0, 0.0, 0.0])
    w_full = buf.get_window()
    assert w_full.shape == (5, 4)
    assert w_full[-1, 0] == 9.0
    assert w_full[0, 0] == 5.0

def test_digital_twin_synchronization_and_stale_detection(sim_config):
    dt_mgr = DigitalTwinSyncManager(sim_config, history_k=10, stale_threshold_s=1.0)
    acq = TelemetryAcquisitionModule(expected_robot_ids=["r01", "r02"])

    # Interval 1 at t=0.0: both robots active
    rec1 = acq.clean_and_package({"r01": {"x": 10, "y": 10}, "r02": {"x": 20, "y": 20}}, [5.0, 1.0, 0.0, 0.1], {}, [], timestamp=0.0)
    info1 = dt_mgr.update_from_telemetry(rec1, wall_clock=0.005)
    assert info1["clock_drift_ms"] == pytest.approx(5.0, rel=1e-1)
    assert len(info1["stale_robots"]) == 0

    # Interval 2 at t=0.5: r02 missing
    rec2 = acq.clean_and_package({"r01": {"x": 10.5, "y": 10}}, [5.1, 1.0, 0.0, 0.1], {}, [], timestamp=0.5)
    info2 = dt_mgr.update_from_telemetry(rec2, wall_clock=0.505)
    assert len(info2["stale_robots"]) == 0  # 0.5s < 1.0s stale threshold

    # Interval 3 at t=1.6: r02 still missing -> elapsed > 1.0s -> stale!
    rec3 = acq.clean_and_package({"r01": {"x": 11.0, "y": 10}}, [5.2, 1.0, 0.0, 0.1], {}, [], timestamp=1.6)
    info3 = dt_mgr.update_from_telemetry(rec3, wall_clock=1.605)
    assert "r02" in info3["stale_robots"]
    assert dt_mgr.stale_state_count >= 1

def test_snapshot_and_rollback(sim_config):
    dt_mgr = DigitalTwinSyncManager(sim_config, history_k=5)
    acq = TelemetryAcquisitionModule(expected_robot_ids=["r01"])

    rec = acq.clean_and_package({"r01": {"x": 12.0, "y": 14.0}}, [8.0, 0.5, 0.01, 0.3], {}, [], timestamp=2.0)
    dt_mgr.update_from_telemetry(rec)
    dt_mgr.record_orchestration_action({"r01": 25.0})

    # Save snapshot
    dt_mgr.take_snapshot("snap_t2")

    # Modify state
    rec_mod = acq.clean_and_package({"r01": {"x": 99.0, "y": 99.0}}, [50.0, 5.0, 0.2, 0.9], {}, [], timestamp=5.0)
    dt_mgr.update_from_telemetry(rec_mod)
    dt_mgr.record_orchestration_action({"r01": 5.0})

    assert dt_mgr.current_system_state[0] == 50.0

    # Rollback
    restored = dt_mgr.restore_snapshot("snap_t2")
    assert restored is True
    assert dt_mgr.current_timestamp == 2.0
    assert dt_mgr.current_system_state[0] == 8.0
    assert dt_mgr.current_allocations["r01"] == 25.0
