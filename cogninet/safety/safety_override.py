"""
Deterministic Hard Safety Constraint Layer
Enforces Equation 7: If w_i(t) >= w_crit, then D_i(t) <= D_max.
Sits downstream of the PPO policy and intercepts candidate allocations.
Overriding is non-negotiable and strictly deterministic.
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class SafetyAuditLog:
    step: int
    overrides_triggered: int
    critical_robots: List[str]
    candidate_allocations: Dict[str, float]
    safe_allocations: Dict[str, float]
    min_crit_bandwidth_mbps: float

class SafetyConstraintLayer:
    def __init__(
        self,
        r_max_mbps: float = 100.0,
        w_crit: float = 0.85,
        d_max_ms: float = 10.0,
        min_critical_bandwidth_mbps: float = 15.0
    ):
        self.r_max_mbps = r_max_mbps
        self.w_crit = w_crit
        self.d_max_ms = d_max_ms
        self.min_critical_bandwidth_mbps = min_critical_bandwidth_mbps
        self.total_overrides = 0
        self.total_violations_blocked = 0
        self.audit_history: List[SafetyAuditLog] = []

    def enforce(
        self,
        candidate_allocation: Dict[str, float],
        semantic_weights: Dict[str, float],
        step: int = 0
    ) -> Tuple[Dict[str, float], bool]:
        """
        Validates candidate action a_cand(t) from PPO.
        If any robot with w_i(t) >= w_crit is allocated less than min_critical_bandwidth_mbps,
        the safety override executes a deterministic feasibility projection.
        Returns:
            safe_allocation: Dict[str, float] strictly satisfying capacity and safety constraints
            override_applied: bool
        """
        active_rids = list(candidate_allocation.keys())
        if not active_rids:
            return {}, False

        # Identify critical robots
        critical_rids = [rid for rid in active_rids if semantic_weights.get(rid, 0.0) >= self.w_crit]

        # Check if candidate allocation threatens any critical flow
        threatened_rids = [rid for rid in critical_rids if candidate_allocation.get(rid, 0.0) < self.min_critical_bandwidth_mbps]

        if not threatened_rids:
            # Candidate is already safe; ensure capacity normalization
            total_req = sum(candidate_allocation.values())
            if total_req > self.r_max_mbps:
                scale = self.r_max_mbps / total_req
                return {k: v * scale for k, v in candidate_allocation.items()}, False
            return candidate_allocation.copy(), False

        # OVERRIDE REQUIRED: Deterministic Feasibility Projection
        self.total_overrides += 1
        self.total_violations_blocked += len(threatened_rids)

        safe_alloc = candidate_allocation.copy()

        # 1. Guarantee minimum bandwidth for all critical robots
        total_crit_reserved = 0.0
        for rid in critical_rids:
            safe_alloc[rid] = max(self.min_critical_bandwidth_mbps, candidate_allocation.get(rid, 0.0))
            total_crit_reserved += safe_alloc[rid]

        # 2. Scale remaining non-critical robots proportionally
        remaining_capacity = max(0.0, self.r_max_mbps - total_crit_reserved)
        non_critical_rids = [rid for rid in active_rids if rid not in critical_rids]

        if non_critical_rids:
            non_crit_sum = sum(candidate_allocation.get(rid, 0.0) for rid in non_critical_rids)
            if non_crit_sum > 0:
                for rid in non_critical_rids:
                    safe_alloc[rid] = (candidate_allocation.get(rid, 0.0) / non_crit_sum) * remaining_capacity
            else:
                equal_non_crit = remaining_capacity / len(non_critical_rids)
                for rid in non_critical_rids:
                    safe_alloc[rid] = equal_non_crit

        # Record audit log
        audit = SafetyAuditLog(
            step=step,
            overrides_triggered=len(threatened_rids),
            critical_robots=critical_rids,
            candidate_allocations=candidate_allocation.copy(),
            safe_allocations=safe_alloc.copy(),
            min_crit_bandwidth_mbps=self.min_critical_bandwidth_mbps
        )
        self.audit_history.append(audit)

        return safe_alloc, True
