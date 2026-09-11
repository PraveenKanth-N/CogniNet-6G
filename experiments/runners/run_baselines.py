"""
Baseline Evaluation Runner
Executes Static Slicing and Reactive Threshold schedulers across all 10 industrial scenarios.
Computes empirical KPIs and saves results to results/tables/baseline_results.csv.
"""

import os
import sys
import json
import yaml
import numpy as np
import pandas as pd
from typing import Dict, List, Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from sim.ros2_ws.factory_world import FactoryWorld
from sim.ros2_ws.fleet_simulator import FleetSimulator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import IndustrialTrafficGenerator, Scenario
from cogninet.telemetry.acquisition import TelemetryAcquisitionModule
from baselines.static_slicing import StaticSlicingScheduler
from baselines.reactive_threshold import ReactiveThresholdScheduler

def run_baseline_scenario(
    scheduler: Any,
    scenario: Scenario,
    config: Dict[str, Any],
    duration_steps: int = 60,
    seed: int = 42,
    num_robots: int = 10,
    channel_deg: float = 1.0
) -> Dict[str, Any]:
    world = FactoryWorld()
    fleet = FleetSimulator(config, world, random_seed=seed)
    net = Ns3NetworkModel(config, random_seed=seed)
    traffic_gen = IndustrialTrafficGenerator(config, seed=seed)
    acq = TelemetryAcquisitionModule(expected_robot_ids=config["fleet"]["robot_ids"][:num_robots])

    latencies = []
    jitters = []
    losses = []
    utilizations = []
    sla_satisfied = []
    crit_delays = []
    reconfigs = 0
    prev_action = None

    dt = config.get("timing", {}).get("delta_t", 0.5)

    for t in range(duration_steps):
        sim_time = t * dt
        e_stop_robot = "r01" if (scenario == Scenario.E_CRITICAL_SAFETY and t in [20, 21]) else None
        fleet_tel = fleet.step(emergency_stop_robot=e_stop_robot)

        packets = traffic_gen.generate_interval_traffic(
            t=t, timestamp=sim_time, scenario=scenario, fleet_telemetry=fleet_tel, num_robots=num_robots
        )
        positions = {rid: (r["x"], r["y"]) for rid, r in fleet_tel.items()}

        # Observable state before this step
        curr_state = [
            float(np.mean(latencies[-5:])) if latencies else 5.0,
            float(np.mean(jitters[-5:])) if jitters else 1.0,
            float(np.mean(losses[-5:])) if losses else 0.01,
            float(np.mean(utilizations[-5:])) if utilizations else 0.1
        ]

        # Scheduler decision
        active_rids = config["fleet"]["robot_ids"][:num_robots]
        if isinstance(scheduler, StaticSlicingScheduler):
            alloc = scheduler.allocate(active_rids)
        elif isinstance(scheduler, ReactiveThresholdScheduler):
            # Pass previous flow metrics if available
            alloc = scheduler.allocate(active_rids, curr_state, flow_metrics={}, step=t)
        else:
            alloc = scheduler.allocate(active_rids)

        # Track reconfiguration thrashing ||a(t) - a(t-1)||
        if prev_action is not None:
            diff = sum(abs(alloc.get(r, 0) - prev_action.get(r, 0)) for r in active_rids)
            if diff > 1e-3:
                reconfigs += 1
        prev_action = alloc.copy()

        # Apply orchestration action to ns-3 model
        net.reallocate(alloc)

        # Transmit
        deg = channel_deg if scenario == Scenario.J_NETWORK_DEGRADATION else 1.0
        state_vec, flow_res = net.transmit_interval(packets, positions, channel_degradation_factor=deg)

        # Package clean telemetry
        rec = acq.clean_and_package(fleet_tel, state_vec, flow_res, packets, timestamp=sim_time)

        latencies.append(rec.system_state[0])
        jitters.append(rec.system_state[1])
        losses.append(rec.system_state[2])
        utilizations.append(rec.system_state[3])

        # SLA compliance: Latency <= 45ms and Loss <= 0.02
        sla_ok = (rec.system_state[0] <= config["network"]["sla_latency_threshold_ms"]) and \
                 (rec.system_state[2] <= config["network"]["sla_packet_loss_max"])
        sla_satisfied.append(int(sla_ok))

        # Check critical message delay
        crit_pkts = [p for p in packets if p.get("is_critical", False)]
        if crit_pkts:
            r01_flow = flow_res.get("r01")
            if r01_flow:
                crit_delays.append(r01_flow.tail_p95_latency_ms)

    sorted_lat = sorted(latencies)
    p95_lat = sorted_lat[int(0.95 * len(sorted_lat))] if sorted_lat else 0.0
    p99_lat = sorted_lat[int(0.99 * len(sorted_lat))] if sorted_lat else 0.0

    return {
        "scheduler": scheduler.name,
        "scenario": scenario.value,
        "mean_latency_ms": round(float(np.mean(latencies)), 2),
        "p95_latency_ms": round(float(p95_lat), 2),
        "p99_latency_ms": round(float(p99_lat), 2),
        "mean_jitter_ms": round(float(np.mean(jitters)), 2),
        "packet_loss_pct": round(float(np.mean(losses) * 100), 2),
        "priority_delay_ms": round(float(np.mean(crit_delays)), 2) if crit_delays else 0.0,
        "sla_satisfaction_pct": round(float(np.mean(sla_satisfied) * 100), 1),
        "resource_utilization_pct": round(float(np.mean(utilizations) * 100), 1),
        "reconfiguration_count": reconfigs
    }

def main():
    print("==================================================================")
    print("   CogniNet-6G Phase 4: Baseline Benchmark Orchestrator Runner    ")
    print("==================================================================\n")

    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    out_dir = os.path.join(REPO_ROOT, "results", "tables")
    os.makedirs(out_dir, exist_ok=True)

    schedulers = [
        StaticSlicingScheduler(r_max_mbps=config["network"]["r_max_mbps"]),
        ReactiveThresholdScheduler(
            r_max_mbps=config["network"]["r_max_mbps"],
            latency_threshold_ms=config["network"]["sla_latency_threshold_ms"],
            loss_threshold=config["network"]["sla_packet_loss_max"]
        )
    ]

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

    all_results = []
    for sched in schedulers:
        print(f"[*] Benchmarking {sched.name}...")
        for sc, n_rob, deg in scenarios:
            res = run_baseline_scenario(
                scheduler=sched,
                scenario=sc,
                config=config,
                duration_steps=60,
                seed=42,
                num_robots=n_rob,
                channel_deg=deg
            )
            all_results.append(res)
            print(f"    -> {sc.value}: P95 Lat={res['p95_latency_ms']}ms, Loss={res['packet_loss_pct']}%, SLA={res['sla_satisfaction_pct']}%")

    df_results = pd.DataFrame(all_results)
    csv_path = os.path.join(out_dir, "baseline_results.csv")
    df_results.to_csv(csv_path, index=False)
    print(f"\n[+] Saved baseline benchmark table to {csv_path}")

    # Summary JSON grouped by scheduler
    summary = df_results.groupby("scheduler").mean(numeric_only=True).to_dict(orient="index")
    json_path = os.path.join(out_dir, "baseline_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[+] Saved baseline summary to {json_path}\n")

if __name__ == "__main__":
    main()
