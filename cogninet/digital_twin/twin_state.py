"""
Module 110: Digital Twin State Structures & Rolling History Buffer
Represents the synchronized digital replica of the physical factory floor and private 6G network.
"""

from typing import Dict, List, Any, Optional
from collections import deque
import numpy as np
from dataclasses import dataclass, field, asdict

@dataclass
class DigitalTwinStateSnapshot:
    step: int
    timestamp: float
    system_state: List[float]                  # S(t) = [L, J, P_L, U]
    robot_fleet: Dict[str, Dict[str, Any]]
    allocations: Dict[str, float]
    last_action: Optional[Dict[str, float]]
    last_reward: Optional[float]
    clock_drift_ms: float
    stale_robots: List[str]

class RollingHistoryBuffer:
    """
    Circular buffer maintaining the historical window of the last k system states S(t-k), ..., S(t).
    Outputs shape (k, 4) numpy array for time-series forecasting in Module 120.
    """
    def __init__(self, capacity: int = 10, feature_dim: int = 4):
        self.capacity = capacity
        self.feature_dim = feature_dim
        self.buffer = deque(maxlen=capacity)

    def append(self, state: List[float]):
        """Append state vector S(t) = [L, J, P_L, U]."""
        if len(state) != self.feature_dim:
            raise ValueError(f"State dimension {len(state)} does not match expected {self.feature_dim}")
        self.buffer.append(list(state))

    def get_window(self) -> np.ndarray:
        """
        Returns numpy array of shape (k, feature_dim).
        If buffer has fewer than k elements, pads with earliest available state.
        """
        if not self.buffer:
            return np.zeros((self.capacity, self.feature_dim), dtype=np.float32)

        data = list(self.buffer)
        if len(data) < self.capacity:
            # Pad front with earliest observation
            pad_count = self.capacity - len(data)
            padded = [data[0]] * pad_count + data
            return np.array(padded, dtype=np.float32)
        return np.array(data, dtype=np.float32)

    def __len__(self):
        return len(self.buffer)
