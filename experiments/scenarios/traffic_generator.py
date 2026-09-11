"""
Industrial Multi-Robot Traffic Generator
Implements Scenarios A through J with strict seed reproducibility and
per-message semantic metadata (task type, urgency, criticality, payload bytes).
"""

import enum
import random
from typing import Dict, List, Any

class Scenario(enum.Enum):
    A_NORMAL = "scenario_A_normal"
    B_CONGESTION_BURST = "scenario_B_congestion_burst"
    C_CAMERA_INSPECTION = "scenario_C_camera_inspection"
    D_ROBOT_CONVERGENCE = "scenario_D_robot_convergence"
    E_CRITICAL_SAFETY = "scenario_E_critical_safety"
    F_MIXED_TRAFFIC = "scenario_F_mixed_traffic"
    G_REPEATED_BURSTS = "scenario_G_repeated_bursts"
    H_UNEXPECTED_SURGE = "scenario_H_unexpected_surge"
    I_ROBOT_SCALING = "scenario_I_robot_scaling"
    J_NETWORK_DEGRADATION = "scenario_J_network_degradation"

# Message Classification Categories
TASK_TYPES = ["TELEMETRY", "NAVIGATION", "MISSION_SYNC", "INSPECTION_VIDEO", "EMERGENCY_STOP"]
MSG_PRIORITIES = {
    "EMERGENCY_STOP": {"urgency": 1.0, "is_critical": True, "flow_type": "URLLC", "size_bytes": 128},
    "NAVIGATION": {"urgency": 0.75, "is_critical": False, "flow_type": "URLLC", "size_bytes": 256},
    "MISSION_SYNC": {"urgency": 0.50, "is_critical": False, "flow_type": "mMTC", "size_bytes": 1024},
    "TELEMETRY": {"urgency": 0.20, "is_critical": False, "flow_type": "mMTC", "size_bytes": 512},
    "INSPECTION_VIDEO": {"urgency": 0.35, "is_critical": False, "flow_type": "eMBB", "size_bytes": 65536}
}

class IndustrialTrafficGenerator:
    def __init__(self, config: Dict[str, Any], seed: int = 42):
        self.config = config
        self.seed = seed
        self.rng = random.Random(seed)
        self.fleet_ids = config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(10)])

    def set_seed(self, seed: int):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_interval_traffic(
        self,
        t: int,
        timestamp: float,
        scenario: Scenario,
        fleet_telemetry: Dict[str, Dict[str, Any]],
        num_robots: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generates packets for control interval t based on selected scenario.
        """
        packets = []
        active_rids = self.fleet_ids[:num_robots]

        # 1. Base periodic telemetry for all active robots (always present)
        for rid in active_rids:
            p_spec = MSG_PRIORITIES["TELEMETRY"]
            packets.append({
                "robot_id": rid,
                "task_type": "TELEMETRY",
                "urgency": p_spec["urgency"],
                "is_critical": p_spec["is_critical"],
                "flow_type": p_spec["flow_type"],
                "payload_bytes": p_spec["size_bytes"],
                "timestamp": timestamp
            })

            # Regular navigation command updates
            if self.rng.random() < 0.8:
                nav_spec = MSG_PRIORITIES["NAVIGATION"]
                packets.append({
                    "robot_id": rid,
                    "task_type": "NAVIGATION",
                    "urgency": nav_spec["urgency"],
                    "is_critical": nav_spec["is_critical"],
                    "flow_type": nav_spec["flow_type"],
                    "payload_bytes": nav_spec["size_bytes"],
                    "timestamp": timestamp
                })

        # Scenario-specific additions:
        if scenario == Scenario.A_NORMAL:
            # Steady baseline: periodic telemetry and light navigation
            pass

        elif scenario == Scenario.B_CONGESTION_BURST:
            # Sudden burst between t=15 and t=25 (e.g. multi-robot status synchronization)
            if 15 <= t <= 25:
                for rid in active_rids[:6]:
                    for _ in range(8):
                        spec = MSG_PRIORITIES["MISSION_SYNC"]
                        packets.append({
                            "robot_id": rid,
                            "task_type": "MISSION_SYNC",
                            "urgency": spec["urgency"],
                            "is_critical": False,
                            "flow_type": spec["flow_type"],
                            "payload_bytes": spec["size_bytes"],
                            "timestamp": timestamp
                        })

        elif scenario == Scenario.C_CAMERA_INSPECTION:
            # Inspection video streams from robots in inspection area
            for rid in active_rids:
                rob = fleet_telemetry.get(rid, {})
                if rob.get("task_state") == "INSPECTING" or (t >= 10 and rid in active_rids[:2]):
                    # Heavy inspection video bursts (multiple 64KB video chunks)
                    for _ in range(6):
                        spec = MSG_PRIORITIES["INSPECTION_VIDEO"]
                        packets.append({
                            "robot_id": rid,
                            "task_type": "INSPECTION_VIDEO",
                            "urgency": spec["urgency"],
                            "is_critical": False,
                            "flow_type": spec["flow_type"],
                            "payload_bytes": spec["size_bytes"],
                            "timestamp": timestamp
                        })

        elif scenario == Scenario.D_ROBOT_CONVERGENCE:
            # Convergence in central aisle creates dense clustered packets
            if 10 <= t <= 30:
                for rid in active_rids[:5]:
                    for _ in range(5):
                        packets.append({
                            "robot_id": rid,
                            "task_type": "NAVIGATION",
                            "urgency": 0.85,
                            "is_critical": False,
                            "flow_type": "URLLC",
                            "payload_bytes": 512,
                            "timestamp": timestamp
                        })

        elif scenario == Scenario.E_CRITICAL_SAFETY:
            # Emergency Stop event at t=20 during an ongoing burst
            if 18 <= t <= 24:
                # Heavy background congestion
                for rid in active_rids:
                    for _ in range(3):
                        packets.append({
                            "robot_id": rid,
                            "task_type": "MISSION_SYNC",
                            "urgency": 0.5,
                            "is_critical": False,
                            "flow_type": "mMTC",
                            "payload_bytes": 2048,
                            "timestamp": timestamp
                        })
            if t == 20 or t == 21:
                # CRITICAL Emergency stop signal on robot r01
                crit_spec = MSG_PRIORITIES["EMERGENCY_STOP"]
                packets.append({
                    "robot_id": "r01",
                    "task_type": "EMERGENCY_STOP",
                    "urgency": crit_spec["urgency"],
                    "is_critical": True,
                    "flow_type": crit_spec["flow_type"],
                    "payload_bytes": crit_spec["size_bytes"],
                    "timestamp": timestamp
                })

        elif scenario == Scenario.F_MIXED_TRAFFIC:
            # All flow classes active simultaneously
            for rid in active_rids:
                if self.rng.random() < 0.4:
                    packets.append({
                        "robot_id": rid,
                        "task_type": "INSPECTION_VIDEO",
                        "urgency": 0.4,
                        "is_critical": False,
                        "flow_type": "eMBB",
                        "payload_bytes": 32768,
                        "timestamp": timestamp
                    })
                if self.rng.random() < 0.1:
                    packets.append({
                        "robot_id": rid,
                        "task_type": "EMERGENCY_STOP",
                        "urgency": 0.95,
                        "is_critical": True,
                        "flow_type": "URLLC",
                        "payload_bytes": 128,
                        "timestamp": timestamp
                    })

        elif scenario == Scenario.G_REPEATED_BURSTS:
            # Periodic bursts every 12 intervals
            if (t % 12) < 4:
                for rid in active_rids[:4]:
                    for _ in range(6):
                        packets.append({
                            "robot_id": rid,
                            "task_type": "MISSION_SYNC",
                            "urgency": 0.6,
                            "is_critical": False,
                            "flow_type": "mMTC",
                            "payload_bytes": 2048,
                            "timestamp": timestamp
                        })

        elif scenario == Scenario.H_UNEXPECTED_SURGE:
            # Extreme out-of-distribution spike
            if 15 <= t <= 18:
                for rid in active_rids:
                    for _ in range(12):
                        packets.append({
                            "robot_id": rid,
                            "task_type": "INSPECTION_VIDEO",
                            "urgency": 0.3,
                            "is_critical": False,
                            "flow_type": "eMBB",
                            "payload_bytes": 65536,
                            "timestamp": timestamp
                        })

        elif scenario == Scenario.I_ROBOT_SCALING:
            # Standard telemetry scaled across N robots
            pass

        elif scenario == Scenario.J_NETWORK_DEGRADATION:
            # Regular traffic, but channel degradation is handled in network layer
            pass

        return packets
