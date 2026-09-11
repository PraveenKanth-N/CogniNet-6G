"""
Module 100: Telemetry Acquisition
Ingests raw telemetry from robot fleet (ROS2/Gazebo) and wireless network (ns-3),
cleans data (interpolates missing values, removes glitches), and outputs canonical timestamped records.
"""

import time
import math
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class CleanRobotTelemetry:
    robot_id: str
    robot_type: str
    x: float
    y: float
    theta: float
    v: float
    w: float
    battery_pct: float
    task_state: str
    current_zone: str
    timestamp: float
    interpolated: bool = False

@dataclass
class CanonicalTelemetryRecord:
    timestamp: float
    control_step: int
    system_state: List[float]                  # S(t) = [L(t), J(t), P_L(t), U(t)]
    robot_fleet: Dict[str, Dict[str, Any]]
    active_messages: List[Dict[str, Any]]
    flow_metrics: Dict[str, Dict[str, Any]]
    glitches_filtered: int
    values_interpolated: int

class TelemetryAcquisitionModule:
    """
    Module 100: Handles ingress cleaning, glitch rejection, and interpolation.
    No AI decisions are made here.
    """
    def __init__(self, expected_robot_ids: List[str] = None):
        self.expected_robot_ids = expected_robot_ids or [f"r{i+1:02d}" for i in range(10)]
        self.previous_robot_states: Dict[str, CleanRobotTelemetry] = {}
        self.step_counter = 0

    def clean_and_package(
        self,
        raw_fleet_telemetry: Dict[str, Dict[str, Any]],
        raw_network_state: List[float],
        raw_flow_results: Dict[str, Any],
        raw_messages: List[Dict[str, Any]],
        timestamp: Optional[float] = None
    ) -> CanonicalTelemetryRecord:
        """
        Cleans and packages raw simulation output into a single timestamped record.
        """
        t_now = timestamp if timestamp is not None else time.time()
        self.step_counter += 1
        glitches_filtered = 0
        values_interpolated = 0

        # 1. Clean Network State Vector S(t) = [L, J, P_L, U]
        cleaned_state = list(raw_network_state)
        # Latency sanity check: [0.0, 5000.0] ms
        if cleaned_state[0] < 0.0 or cleaned_state[0] > 5000.0:
            cleaned_state[0] = max(0.0, min(5000.0, cleaned_state[0]))
            glitches_filtered += 1
        # Jitter sanity check: [0.0, 2000.0] ms
        if cleaned_state[1] < 0.0 or cleaned_state[1] > 2000.0:
            cleaned_state[1] = max(0.0, min(2000.0, cleaned_state[1]))
            glitches_filtered += 1
        # Packet loss ratio: [0.0, 1.0]
        if cleaned_state[2] < 0.0 or cleaned_state[2] > 1.0:
            cleaned_state[2] = max(0.0, min(1.0, cleaned_state[2]))
            glitches_filtered += 1
        # Resource utilization: [0.0, 1.0]
        if cleaned_state[3] < 0.0 or cleaned_state[3] > 1.0:
            cleaned_state[3] = max(0.0, min(1.0, cleaned_state[3]))
            glitches_filtered += 1

        # 2. Clean and Interpolate Robot Fleet Telemetry
        cleaned_fleet: Dict[str, Dict[str, Any]] = {}

        for rid in self.expected_robot_ids:
            if rid in raw_fleet_telemetry:
                r_raw = raw_fleet_telemetry[rid]

                # Glitch filtering on coordinates: Factory is 100m x 80m
                x = max(0.0, min(100.0, float(r_raw.get("x", 0.0))))
                y = max(0.0, min(80.0, float(r_raw.get("y", 0.0))))
                if x != r_raw.get("x") or y != r_raw.get("y"):
                    glitches_filtered += 1

                # Battery percentage sanity check [0, 100]
                batt = max(0.0, min(100.0, float(r_raw.get("battery_pct", 100.0))))

                clean_rob = CleanRobotTelemetry(
                    robot_id=rid,
                    robot_type=r_raw.get("robot_type", "AMR"),
                    x=x,
                    y=y,
                    theta=float(r_raw.get("theta", 0.0)),
                    v=float(r_raw.get("v", 0.0)),
                    w=float(r_raw.get("w", 0.0)),
                    battery_pct=batt,
                    task_state=r_raw.get("task_state", "NAVIGATING"),
                    current_zone=r_raw.get("current_zone", "general_transit"),
                    timestamp=t_now,
                    interpolated=False
                )
                self.previous_robot_states[rid] = clean_rob
                cleaned_fleet[rid] = asdict(clean_rob)
            else:
                # Robot is missing from current interval -> Interpolate from previous state
                values_interpolated += 1
                if rid in self.previous_robot_states:
                    prev = self.previous_robot_states[rid]
                    # Dead-reckoning kinematic interpolation
                    dt = 0.5
                    new_theta = prev.theta + prev.w * dt
                    new_x = max(0.0, min(100.0, prev.x + prev.v * math.cos(new_theta) * dt))
                    new_y = max(0.0, min(80.0, prev.y + prev.v * math.sin(new_theta) * dt))
                    interpolated_rob = CleanRobotTelemetry(
                        robot_id=rid,
                        robot_type=prev.robot_type,
                        x=new_x,
                        y=new_y,
                        theta=new_theta,
                        v=prev.v,
                        w=prev.w,
                        battery_pct=max(0.0, prev.battery_pct - 0.005),
                        task_state=prev.task_state,
                        current_zone=prev.current_zone,
                        timestamp=t_now,
                        interpolated=True
                    )
                    self.previous_robot_states[rid] = interpolated_rob
                    cleaned_fleet[rid] = asdict(interpolated_rob)
                else:
                    # Initial default if never seen before
                    default_rob = CleanRobotTelemetry(
                        robot_id=rid,
                        robot_type="AMR",
                        x=50.0,
                        y=40.0,
                        theta=0.0,
                        v=0.0,
                        w=0.0,
                        battery_pct=100.0,
                        task_state="NAVIGATING",
                        current_zone="general_transit",
                        timestamp=t_now,
                        interpolated=True
                    )
                    self.previous_robot_states[rid] = default_rob
                    cleaned_fleet[rid] = asdict(default_rob)

        # 3. Clean Message Metadata
        cleaned_messages = []
        for m in raw_messages:
            urgency = max(0.0, min(1.0, float(m.get("urgency", 0.1))))
            cleaned_messages.append({
                "robot_id": m.get("robot_id", "unknown"),
                "task_type": m.get("task_type", "TELEMETRY"),
                "urgency": urgency,
                "is_critical": bool(m.get("is_critical", False)),
                "flow_type": m.get("flow_type", "mMTC"),
                "payload_bytes": max(1, int(m.get("payload_bytes", 128))),
                "timestamp": float(m.get("timestamp", t_now))
            })

        # 4. Clean Flow Results
        cleaned_flows = {}
        for rid, flow in raw_flow_results.items():
            if hasattr(flow, "__dict__"):
                cleaned_flows[rid] = asdict(flow)
            else:
                cleaned_flows[rid] = dict(flow)

        return CanonicalTelemetryRecord(
            timestamp=round(t_now, 4),
            control_step=self.step_counter,
            system_state=cleaned_state,
            robot_fleet=cleaned_fleet,
            active_messages=cleaned_messages,
            flow_metrics=cleaned_flows,
            glitches_filtered=glitches_filtered,
            values_interpolated=values_interpolated
        )
