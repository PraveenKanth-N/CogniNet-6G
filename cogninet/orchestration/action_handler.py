"""
Action Dispatch & Slicing Actuator (Module 150)
Translates network slicing decisions into runtime ns-3 radio configurations,
verifies physical capacity invariants, and tracks actuator overhead.
"""

import time
from typing import Dict, List, Any, Tuple, Optional

class ActionHandler:
    """
    Module 150: Actuator interface enforcing 6G slice reconfiguration.
    Validates capacity bounds, tracks actuator jitter, and applies allocations.
    """
    def __init__(self, r_max_mbps: float = 100.0, tolerance: float = 1e-3):
        self.r_max_mbps = float(r_max_mbps)
        self.tolerance = tolerance
        self.dispatch_history: List[Dict[str, Any]] = []

    def validate_allocation(self, allocation_vector: Dict[str, float]) -> Tuple[bool, str]:
        """
        Validates whether allocation vector satisfies non-negativity and capacity sum.
        """
        for rid, bw in allocation_vector.items():
            if bw < -self.tolerance:
                return False, f"Negative bandwidth allocated to {rid}: {bw:.4f} Mbps"

        total_bw = sum(allocation_vector.values())
        if total_bw > (self.r_max_mbps + self.tolerance):
            return False, f"Total allocated bandwidth ({total_bw:.4f} Mbps) exceeds R_max ({self.r_max_mbps:.4f} Mbps)"

        return True, "Valid"

    def compute_reconfiguration_cost(
        self,
        current_alloc: Dict[str, float],
        previous_alloc: Optional[Dict[str, float]]
    ) -> float:
        """
        Computes L2 reconfiguration norm: ||a(t) - a(t-1)|| / R_max.
        """
        if not previous_alloc:
            return 0.0

        sq_diff = 0.0
        for rid, curr_bw in current_alloc.items():
            prev_bw = previous_alloc.get(rid, 0.0)
            sq_diff += (curr_bw - prev_bw) ** 2

        norm = (sq_diff ** 0.5) / self.r_max_mbps
        return float(norm)

    def dispatch(
        self,
        net_model: Any,
        allocation_vector: Dict[str, float],
        timestamp: float,
        previous_alloc: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches validated slice allocations to the network simulation model.
        Returns execution telemetry.
        """
        start_time = time.perf_counter()

        is_valid, reason = self.validate_allocation(allocation_vector)
        if not is_valid:
            raise ValueError(f"ActionHandler dispatch rejected invalid allocation: {reason}")

        reconfig_cost = self.compute_reconfiguration_cost(allocation_vector, previous_alloc)

        # Apply to ns-3 network model
        net_model.reallocate(allocation_vector)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        record = {
            "timestamp": timestamp,
            "total_allocated_mbps": round(sum(allocation_vector.values()), 4),
            "reconfiguration_cost": round(reconfig_cost, 6),
            "actuator_latency_ms": round(elapsed_ms, 4),
            "num_slices": len(allocation_vector)
        }
        self.dispatch_history.append(record)
        return record
