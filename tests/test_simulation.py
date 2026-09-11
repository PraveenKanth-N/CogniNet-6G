"""
Unit and Integration Tests for Phase 2: Robot & Network Simulation
Validates factory layout, fleet kinematics, ns-3 network model, traffic generation,
and deterministic dataset reproduction.
"""

import os
import yaml
import pytest
import pandas as pd
from sim.ros2_ws.factory_world import FactoryWorld
from sim.ros2_ws.fleet_simulator import FleetSimulator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import IndustrialTrafficGenerator, Scenario
from experiments.runners.run_sim_telemetry import run_scenario_simulation

@pytest.fixture
def sim_config():
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_factory_world():
    world = FactoryWorld()
    assert world.width == 100.0
    assert world.height == 80.0
    assert len(world.zones) == 4
    assert len(world.waypoints) >= 4
    assert len(world.base_stations) == 2

    # Test zone location
    z = world.get_zone_for_position(10.0, 10.0)
    assert z == "loading_dock"
    z_insp = world.get_zone_for_position(85.0, 60.0)
    assert z_insp == "inspection_station"

def test_fleet_simulator_kinematics(sim_config):
    world = FactoryWorld()
    fleet = FleetSimulator(sim_config, world, random_seed=42)
    assert len(fleet.robots) == 10

    # Step simulation
    t1 = fleet.step()
    assert len(t1) == 10
    r01 = t1["r01"]
    assert "x" in r01 and "y" in r01 and "theta" in r01
    assert "battery_pct" in r01
    assert 0.0 <= r01["battery_pct"] <= 100.0

    # Test emergency stop transition
    t2 = fleet.step(emergency_stop_robot="r01")
    assert t2["r01"]["task_state"] == "EMERGENCY_STOP"
    assert t2["r01"]["v"] == 0.0

def test_ns3_network_model(sim_config):
    net = Ns3NetworkModel(sim_config, random_seed=42)
    assert sum(net.current_allocations.values()) == pytest.approx(100.0, rel=1e-3)

    # Reallocate with scaling test
    req = {rid: 20.0 for rid in net.robot_ids}  # 200 Mbps total > 100 Mbps
    net.reallocate(req)
    assert sum(net.current_allocations.values()) <= 100.001

    # Transmit test packet
    packets = [{
        "robot_id": "r01",
        "task_type": "EMERGENCY_STOP",
        "urgency": 1.0,
        "is_critical": True,
        "flow_type": "URLLC",
        "payload_bytes": 128,
        "timestamp": 0.0
    }]
    positions = {"r01": (35.0, 42.0)}
    state_vec, flow_res = net.transmit_interval(packets, positions)

    assert len(state_vec) == 4  # [L, J, P_L, U]
    assert state_vec[0] >= 0.0  # Latency >= 0
    assert 0.0 <= state_vec[2] <= 1.0  # Loss in [0, 1]
    assert 0.0 <= state_vec[3] <= 1.0  # Utilization in [0, 1]

def test_traffic_generator_scenarios(sim_config):
    tg = IndustrialTrafficGenerator(sim_config, seed=42)
    fleet_mock = {f"r{i+1:02d}": {"task_state": "NAVIGATING"} for i in range(10)}

    # Normal traffic
    pkts_a = tg.generate_interval_traffic(0, 0.0, Scenario.A_NORMAL, fleet_mock, num_robots=10)
    assert len(pkts_a) >= 10

    # Congestion burst at t=20
    pkts_b = tg.generate_interval_traffic(20, 10.0, Scenario.B_CONGESTION_BURST, fleet_mock, num_robots=10)
    assert len(pkts_b) > len(pkts_a)

    # Critical safety event at t=20
    pkts_e = tg.generate_interval_traffic(20, 10.0, Scenario.E_CRITICAL_SAFETY, fleet_mock, num_robots=10)
    crit_pkts = [p for p in pkts_e if p["is_critical"]]
    assert len(crit_pkts) >= 1
    assert crit_pkts[0]["task_type"] == "EMERGENCY_STOP"

def test_reproducibility_across_seeds(sim_config):
    df1 = run_scenario_simulation(Scenario.A_NORMAL, sim_config, duration_steps=10, seed=123)
    df2 = run_scenario_simulation(Scenario.A_NORMAL, sim_config, duration_steps=10, seed=123)
    pd.testing.assert_frame_equal(df1, df2)
