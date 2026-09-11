"""
Kinematic Robot Fleet Simulator
Simulates N autonomous robots (AMRs/AGVs) navigating an industrial facility with
differential-drive kinematics, battery discharge, and operational state machines.
"""

import math
import random
from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class RobotState:
    robot_id: str
    robot_type: str        # "AMR" (autonomous mobile robot) or "AGV" (guided vehicle)
    x: float               # meters
    y: float               # meters
    theta: float           # heading angle (radians)
    v: float               # linear velocity (m/s)
    w: float               # angular velocity (rad/s)
    battery_pct: float     # State of charge [0, 100]
    task_state: str        # "IDLE", "NAVIGATING", "INSPECTING", "OBSTACLE_WAIT", "CHARGING", "EMERGENCY_STOP"
    target_waypoint: str
    current_zone: str

class FleetSimulator:
    def __init__(self, config: Dict[str, Any], factory_world: Any, random_seed: int = 42):
        self.config = config
        self.world = factory_world
        self.num_robots = config.get("fleet", {}).get("num_robots", 10)
        self.robot_ids = config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(self.num_robots)])
        self.dt = config.get("timing", {}).get("delta_t", 0.5)
        self.rng = random.Random(random_seed)

        self.robots: Dict[str, RobotState] = {}
        self._init_fleet()

    def _init_fleet(self):
        wp_keys = list(self.world.waypoints.keys())
        for i, rid in enumerate(self.robot_ids):
            # Stagger initial positions across waypoints
            start_wp = wp_keys[i % len(wp_keys)]
            wx, wy = self.world.waypoints[start_wp]
            # Add small initial offset
            x = wx + self.rng.uniform(-2.0, 2.0)
            y = wy + self.rng.uniform(-2.0, 2.0)
            rtype = "AMR" if i % 2 == 0 else "AGV"
            target_wp = wp_keys[(i + 1) % len(wp_keys)]
            zone = self.world.get_zone_for_position(x, y)

            self.robots[rid] = RobotState(
                robot_id=rid,
                robot_type=rtype,
                x=x,
                y=y,
                theta=self.rng.uniform(-math.pi, math.pi),
                v=0.0,
                w=0.0,
                battery_pct=self.rng.uniform(85.0, 100.0),
                task_state="NAVIGATING",
                target_waypoint=target_wp,
                current_zone=zone
            )

    def step(self, emergency_stop_robot: str = None) -> Dict[str, Dict[str, Any]]:
        """Advance fleet kinematics by one delta_t control interval."""
        telemetry = {}
        wp_keys = list(self.world.waypoints.keys())

        for rid, rob in self.robots.items():
            if emergency_stop_robot and rid == emergency_stop_robot:
                rob.task_state = "EMERGENCY_STOP"
                rob.v = 0.0
                rob.w = 0.0
            elif rob.task_state == "EMERGENCY_STOP":
                rob.v = 0.0
                rob.w = 0.0
            elif rob.task_state == "NAVIGATING":
                target_x, target_y = self.world.waypoints[rob.target_waypoint]
                dx = target_x - rob.x
                dy = target_y - rob.y
                dist = math.hypot(dx, dy)
                desired_theta = math.atan2(dy, dx)
                d_theta = (desired_theta - rob.theta + math.pi) % (2 * math.pi) - math.pi

                if dist < 1.5:
                    # Reached waypoint -> transition state
                    if "INSPECT" in rob.target_waypoint:
                        rob.task_state = "INSPECTING"
                        rob.v = 0.0
                        rob.w = 0.0
                    else:
                        # Pick next waypoint
                        next_idx = (wp_keys.index(rob.target_waypoint) + 1) % len(wp_keys)
                        rob.target_waypoint = wp_keys[next_idx]
                else:
                    # Differential-drive kinematic update
                    max_v = 1.2 if rob.robot_type == "AMR" else 0.8  # m/s
                    rob.v = min(max_v, dist * 0.8)
                    rob.w = max(-1.0, min(1.0, d_theta * 1.5))
                    rob.theta += rob.w * self.dt
                    rob.x += rob.v * math.cos(rob.theta) * self.dt
                    rob.y += rob.v * math.sin(rob.theta) * self.dt
                    rob.battery_pct = max(5.0, rob.battery_pct - 0.01 * self.dt * (1.0 + rob.v))

            elif rob.task_state == "INSPECTING":
                rob.v = 0.0
                rob.w = 0.0
                rob.battery_pct = max(5.0, rob.battery_pct - 0.02 * self.dt)
                # After small duration, return to navigation
                if self.rng.random() < 0.2:
                    rob.task_state = "NAVIGATING"
                    next_idx = (wp_keys.index(rob.target_waypoint) + 1) % len(wp_keys)
                    rob.target_waypoint = wp_keys[next_idx]

            rob.current_zone = self.world.get_zone_for_position(rob.x, rob.y)
            telemetry[rid] = asdict(rob)

        return telemetry
