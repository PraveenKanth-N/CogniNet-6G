"""
Baseline 1: Static Resource Slicing
Fixed uniform bandwidth allocation across all active robots in the fleet.
Capacity constraint Sum(R_i(t)) <= R_max is strictly enforced.
"""

from typing import Dict, List, Any

class StaticSlicingScheduler:
    def __init__(self, r_max_mbps: float = 100.0):
        self.r_max_mbps = r_max_mbps
        self.name = "Static Slicing"

    def allocate(
        self,
        active_robot_ids: List[str],
        current_state: List[float] = None,
        messages: List[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Uniformly divides total capacity R_max equally across active robots.
        Returns: {robot_id: bandwidth_mbps}
        """
        n = len(active_robot_ids)
        if n == 0:
            return {}
        share = self.r_max_mbps / n
        return {rid: share for rid in active_robot_ids}
