"""
Co-Simulation Telemetry Driver & Raw Dataset Generator
Simulates the joint Robot Fleet (kinematics) + ns-3 Network Model (packet transmissions)
across all 10 industrial scenarios and persists empirical raw datasets to datasets/raw/.
"""

import os
import sys
import json
import yaml
import pandas as pd
from typing import Dict, Any

# Ensure repository root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from sim.ros2_ws.factory_world import FactoryWorld
from sim.ros2_ws.fleet_simulator import FleetSimulator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import IndustrialTrafficGenerator, Scenario

def run_scenario_simulation(
    scenario: Scenario,
    config: Dict[str, Any],
    duration_steps: int = 60,
    seed: int = 42,
    num_robots: int = 10,
    channel_degradation: float = 1.0
) -> pd.DataFrame:
    """Runs co-simulation for one scenario and returns telemetry DataFrame."""
    world = FactoryWorld()
    fleet = FleetSimulator(config, world, random_seed=seed)
    net = Ns3NetworkModel(config, random_seed=seed)
    traffic_gen = IndustrialTrafficGenerator(config, seed=seed)

    records = []
    dt = config.get("timing", {}).get("delta_t", 0.5)

    for t in range(duration_steps):
        sim_time = t * dt

        # Handle emergency stop trigger in Scenario E
        e_stop_robot = "r01" if (scenario == Scenario.E_CRITICAL_SAFETY and t in [20, 21]) else None
        fleet_telemetry = fleet.step(emergency_stop_robot=e_stop_robot)

        # Generate traffic for this interval
        packets = traffic_gen.generate_interval_traffic(
            t=t,
            timestamp=sim_time,
            scenario=scenario,
            fleet_telemetry=fleet_telemetry,
            num_robots=num_robots
        )

        # Robot positions
        robot_positions = {rid: (rob["x"], rob["y"]) for rid, rob in fleet_telemetry.items()}

        # Network transmission
        deg = channel_degradation if scenario == Scenario.J_NETWORK_DEGRADATION else 1.0
        state_vec, flow_results = net.transmit_interval(packets, robot_positions, channel_degradation_factor=deg)

        # Check SLA compliance: Latency <= 45ms and Packet Loss <= 0.02
        sla_satisfied = (state_vec[0] <= config.get("network", {}).get("sla_latency_threshold_ms", 45.0)) and \
                        (state_vec[2] <= config.get("network", {}).get("sla_packet_loss_max", 0.02))

        # Check critical message delay
        crit_pkts = [p for p in packets if p.get("is_critical", False)]
        crit_delay = 0.0
        if crit_pkts:
            r01_flow = flow_results.get("r01")
            crit_delay = r01_flow.tail_p95_latency_ms if r01_flow else 0.0

        records.append({
            "step": t,
            "timestamp": round(sim_time, 2),
            "scenario": scenario.value,
            "latency_ms": state_vec[0],
            "jitter_ms": state_vec[1],
            "packet_loss_ratio": state_vec[2],
            "resource_utilization": state_vec[3],
            "sla_satisfied": int(sla_satisfied),
            "critical_traffic_present": int(len(crit_pkts) > 0),
            "critical_message_delay_ms": crit_delay,
            "active_robots": num_robots,
            "total_packets_generated": len(packets)
        })

    return pd.DataFrame(records)

def main():
    print("==================================================================")
    print("  CogniNet-6G Phase 2: Generating Co-Simulation Telemetry Datasets")
    print("==================================================================\n")

    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    out_dir = os.path.join(REPO_ROOT, "datasets", "raw")
    os.makedirs(out_dir, exist_ok=True)

    metadata = {
        "dataset_version": "1.0.0",
        "random_seed": 42,
        "delta_t": config["timing"]["delta_t"],
        "r_max_mbps": config["network"]["r_max_mbps"],
        "scenarios": {}
    }

    scenarios = [
        (Scenario.A_NORMAL, 10, 1.0),
        (Scenario.B_CONGESTION_BURST, 10, 1.0),
        (Scenario.C_CAMERA_INSPECTION, 10, 1.0),
        (Scenario.D_ROBOT_CONVERGENCE, 10, 1.0),
        (Scenario.E_CRITICAL_SAFETY, 10, 1.0),
        (Scenario.F_MIXED_TRAFFIC, 10, 1.0),
        (Scenario.G_REPEATED_BURSTS, 10, 1.0),
        (Scenario.H_UNEXPECTED_SURGE, 10, 1.0),
        (Scenario.I_ROBOT_SCALING, 20, 1.0),
        (Scenario.J_NETWORK_DEGRADATION, 10, 1.4)
    ]

    for sc, n_rob, deg in scenarios:
        print(f"[*] Simulating {sc.value} (N={n_rob}, channel_factor={deg})...")
        df = run_scenario_simulation(
            scenario=sc,
            config=config,
            duration_steps=60,
            seed=42,
            num_robots=n_rob,
            channel_degradation=deg
        )
        csv_file = os.path.join(out_dir, f"{sc.value}.csv")
        df.to_csv(csv_file, index=False)
        print(f"    -> Saved {len(df)} telemetry samples to {csv_file}")

        metadata["scenarios"][sc.value] = {
            "file": f"{sc.value}.csv",
            "samples": len(df),
            "num_robots": n_rob,
            "mean_latency_ms": round(float(df["latency_ms"].mean()), 2),
            "mean_packet_loss": round(float(df["packet_loss_ratio"].mean()), 4),
            "mean_utilization": round(float(df["resource_utilization"].mean()), 3),
            "sla_satisfaction_pct": round(float(df["sla_satisfied"].mean() * 100), 1)
        }

    meta_file = os.path.join(out_dir, "dataset_metadata.json")
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"\n[+] All 10 scenario datasets generated and metadata logged to {meta_file}\n")

if __name__ == "__main__":
    main()
