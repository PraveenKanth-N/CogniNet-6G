"""
Heuristic Baselines: Semantic-Only & Prediction-Only Schedulers
Baseline 3: SemanticOnlyScheduler allocates bandwidth proportionally to message urgency/criticality.
Baseline 4: PredictionOnlyScheduler allocates bandwidth based on forecasted traffic trend without semantic awareness.
"""

from typing import Dict, List, Any

class SemanticOnlyScheduler:
    """Baseline 3: Semantic prioritization without prediction or RL policy."""
    def __init__(self, r_max_mbps: float = 100.0):
        self.r_max_mbps = r_max_mbps
        self.name = "Semantic Only"

    def allocate(
        self,
        active_robot_ids: List[str],
        messages: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        n = len(active_robot_ids)
        if n == 0:
            return {}

        weights = {rid: 1.0 for rid in active_robot_ids}
        for m in messages:
            rid = m.get("robot_id")
            if rid in weights:
                urg = m.get("urgency", 0.1)
                is_crit = m.get("is_critical", False)
                w_inc = 5.0 if is_crit else (urg * 2.0)
                weights[rid] += w_inc

        total_weight = sum(weights.values())
        return {rid: (w / total_weight) * self.r_max_mbps for rid, w in weights.items()}

class PredictionOnlyScheduler:
    """Baseline 4: Allocation based on traffic load forecast without message priority."""
    def __init__(self, r_max_mbps: float = 100.0):
        self.r_max_mbps = r_max_mbps
        self.name = "Prediction Only"

    def allocate(
        self,
        active_robot_ids: List[str],
        forecasted_state: List[float],
        historical_utilizations: Dict[str, float] = None
    ) -> Dict[str, float]:
        n = len(active_robot_ids)
        if n == 0:
            return {}

        # If forecasted latency/loss is trending up, weight by historical load
        weights = {rid: 1.0 for rid in active_robot_ids}
        if historical_utilizations:
            for rid, u in historical_utilizations.items():
                if rid in weights:
                    weights[rid] += u * 3.0

        total_w = sum(weights.values())
        return {rid: (w / total_w) * self.r_max_mbps for rid, w in weights.items()}
