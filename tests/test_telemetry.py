"""
Unit Tests for Module 100: Telemetry Acquisition
Tests cleaning, physical bounds checks, glitch filtering, and missing data interpolation.
"""

import pytest
from cogninet.telemetry.acquisition import TelemetryAcquisitionModule, CanonicalTelemetryRecord

def test_telemetry_cleaning_and_bounds():
    acq = TelemetryAcquisitionModule(expected_robot_ids=["r01", "r02"])

    # Raw inputs with intentional glitches:
    # Negative latency, out-of-bound coordinates, negative battery
    raw_fleet = {
        "r01": {"robot_type": "AMR", "x": 150.0, "y": -20.0, "battery_pct": 105.0, "task_state": "NAVIGATING"},
        "r02": {"robot_type": "AGV", "x": 40.0, "y": 30.0, "battery_pct": -5.0, "task_state": "NAVIGATING"}
    }
    raw_net = [-10.0, 5.0, 1.5, -0.2]  # Negative latency, loss > 1, utilization < 0
    raw_flows = {}
    raw_msgs = [{"robot_id": "r01", "urgency": 1.5, "is_critical": True}]

    record = acq.clean_and_package(
        raw_fleet_telemetry=raw_fleet,
        raw_network_state=raw_net,
        raw_flow_results=raw_flows,
        raw_messages=raw_msgs,
        timestamp=10.0
    )

    assert isinstance(record, CanonicalTelemetryRecord)
    # Check that network state was clamped to valid ranges
    assert record.system_state[0] == 0.0   # Latency clamped from -10 to 0
    assert record.system_state[2] == 1.0   # Loss clamped from 1.5 to 1.0
    assert record.system_state[3] == 0.0   # Util clamped from -0.2 to 0.0

    # Check robot coordinates clamped to factory bounds [0..100, 0..80]
    assert record.robot_fleet["r01"]["x"] == 100.0
    assert record.robot_fleet["r01"]["y"] == 0.0
    assert record.robot_fleet["r01"]["battery_pct"] == 100.0
    assert record.robot_fleet["r02"]["battery_pct"] == 0.0

    # Glitches recorded
    assert record.glitches_filtered > 0
    assert record.values_interpolated == 0

def test_missing_robot_interpolation():
    acq = TelemetryAcquisitionModule(expected_robot_ids=["r01", "r02"])

    # Step 1: Provide both robots
    raw_fleet_1 = {
        "r01": {"x": 10.0, "y": 10.0, "theta": 0.0, "v": 1.0, "w": 0.0, "battery_pct": 90.0},
        "r02": {"x": 20.0, "y": 20.0, "theta": 0.0, "v": 0.5, "w": 0.0, "battery_pct": 85.0}
    }
    rec1 = acq.clean_and_package(raw_fleet_1, [10.0, 1.0, 0.01, 0.5], {}, [], timestamp=1.0)
    assert rec1.values_interpolated == 0
    assert not rec1.robot_fleet["r01"]["interpolated"]

    # Step 2: Robot r02 packet is dropped / missing
    raw_fleet_2 = {
        "r01": {"x": 10.5, "y": 10.0, "theta": 0.0, "v": 1.0, "w": 0.0, "battery_pct": 89.9}
    }
    rec2 = acq.clean_and_package(raw_fleet_2, [10.2, 1.1, 0.01, 0.5], {}, [], timestamp=1.5)
    assert rec2.values_interpolated == 1
    assert rec2.robot_fleet["r02"]["interpolated"] is True
    # r02 x should be dead-reckoned forward: x + v * dt = 20.0 + 0.5 * 0.5 = 20.25
    assert rec2.robot_fleet["r02"]["x"] == pytest.approx(20.25, rel=1e-2)
