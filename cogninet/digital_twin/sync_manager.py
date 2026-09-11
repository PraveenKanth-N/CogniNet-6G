"""
Module 110: Digital Twin Synchronization Manager
Maintains twin state tables, monitors timestamp drift and stale robot states,
supports snapshot/rollback for debugging, and provides experiment replay logging.
"""

import time
import json
import copy
from typing import Dict, List, Any, Optional
import numpy as np
from cogninet.telemetry.acquisition import CanonicalTelemetryRecord
from cogninet.digital_twin.twin_state import DigitalTwinStateSnapshot, RollingHistoryBuffer

class DigitalTwinSyncManager:
    """
    Module 110: The authoritative shared state store and memory of the CogniNet-6G closed loop.
    Supports in-memory operations and optional Redis synchronization.
    """
    def __init__(self, config: Dict[str, Any], history_k: int = 10, stale_threshold_s: float = 2.0):
        self.config = config
        self.history_k = history_k
        self.stale_threshold_s = stale_threshold_s

        # Rolling history buffer for S(t-k), ..., S(t)
        self.history_buffer = RollingHistoryBuffer(capacity=history_k, feature_dim=4)

        # Current State
        self.current_step = 0
        self.current_timestamp = 0.0
        self.current_system_state = [0.0, 0.0, 0.0, 0.0]
        self.current_fleet: Dict[str, Dict[str, Any]] = {}
        self.current_allocations: Dict[str, float] = {}
        self.last_action: Optional[Dict[str, float]] = None
        self.last_reward: Optional[float] = None

        # Synchronization quality metrics
        self.last_robot_update_times: Dict[str, float] = {}
        self.clock_drift_history: List[float] = []
        self.stale_state_count = 0
        self.missing_update_count = 0

        # Snapshot archive & Replay log
        self.snapshots: Dict[str, DigitalTwinStateSnapshot] = {}
        self.replay_log: List[Dict[str, Any]] = []

    def update_from_telemetry(self, record: CanonicalTelemetryRecord, wall_clock: Optional[float] = None) -> Dict[str, Any]:
        """
        Updates the Digital Twin state table with a new cleaned telemetry record.
        Performs drift analysis and stale-state detection.
        """
        now = wall_clock if wall_clock is not None else time.time()
        self.current_step = record.control_step
        self.current_timestamp = record.timestamp
        self.current_system_state = list(record.system_state)
        self.current_fleet = copy.deepcopy(record.robot_fleet)

        # Push S(t) into rolling history
        self.history_buffer.append(self.current_system_state)

        # 1. Clock drift estimation: difference between simulation timestamp and wall clock
        drift_ms = abs(now - record.timestamp) * 1000.0 if wall_clock is not None else 0.0
        self.clock_drift_history.append(drift_ms)

        # 2. Stale-state detection across robot fleet
        stale_robots = []
        for rid, rob in self.current_fleet.items():
            if not rob.get("interpolated", False):
                self.last_robot_update_times[rid] = record.timestamp
            else:
                last_seen = self.last_robot_update_times.get(rid, 0.0)
                if (record.timestamp - last_seen) > self.stale_threshold_s:
                    stale_robots.append(rid)
                    self.stale_state_count += 1

        if record.values_interpolated > 0:
            self.missing_update_count += record.values_interpolated

        # Record into replay log
        transition = {
            "step": self.current_step,
            "timestamp": self.current_timestamp,
            "system_state": list(self.current_system_state),
            "stale_robots": stale_robots,
            "drift_ms": round(drift_ms, 2)
        }
        self.replay_log.append(transition)

        return {
            "step": self.current_step,
            "timestamp": self.current_timestamp,
            "system_state": self.current_system_state,
            "clock_drift_ms": round(drift_ms, 2),
            "stale_robots": stale_robots,
            "history_depth": len(self.history_buffer)
        }

    def record_orchestration_action(self, action: Dict[str, float]):
        """Records the network action a(t) chosen by Module 140 / Module 150."""
        self.last_action = copy.deepcopy(action)
        self.current_allocations = copy.deepcopy(action)
        if self.replay_log:
            self.replay_log[-1]["action"] = copy.deepcopy(action)

    def record_feedback(self, reward: float, post_action_state: List[float]):
        """Module 170 feedback: writes post-action state S(t+1) and reward r(t) into the twin."""
        self.last_reward = reward
        if self.replay_log:
            self.replay_log[-1]["reward"] = round(reward, 4)
            self.replay_log[-1]["post_action_state"] = list(post_action_state)

    def get_history_window(self) -> np.ndarray:
        """Returns the rolling historical sequence [S(t-k), ..., S(t)] of shape (k, 4)."""
        return self.history_buffer.get_window()

    def get_current_snapshot(self) -> DigitalTwinStateSnapshot:
        """Returns a complete immutable snapshot of the current twin state."""
        return DigitalTwinStateSnapshot(
            step=self.current_step,
            timestamp=self.current_timestamp,
            system_state=list(self.current_system_state),
            robot_fleet=copy.deepcopy(self.current_fleet),
            allocations=copy.deepcopy(self.current_allocations),
            last_action=copy.deepcopy(self.last_action) if self.last_action else None,
            last_reward=self.last_reward,
            clock_drift_ms=self.clock_drift_history[-1] if self.clock_drift_history else 0.0,
            stale_robots=[]
        )

    def take_snapshot(self, snapshot_id: str):
        """Archives current twin state for debugging or potential rollback."""
        self.snapshots[snapshot_id] = self.get_current_snapshot()

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """Restores twin state from a previously saved snapshot."""
        if snapshot_id not in self.snapshots:
            return False
        snap = self.snapshots[snapshot_id]
        self.current_step = snap.step
        self.current_timestamp = snap.timestamp
        self.current_system_state = list(snap.system_state)
        self.current_fleet = copy.deepcopy(snap.robot_fleet)
        self.current_allocations = copy.deepcopy(snap.allocations)
        self.last_action = copy.deepcopy(snap.last_action)
        self.last_reward = snap.last_reward
        return True

    def export_replay_log(self, filepath: str):
        """Exports experiment replay log to JSON for exact deterministic re-runs."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.replay_log, f, indent=2)
