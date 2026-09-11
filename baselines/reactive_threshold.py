"""
Baseline 2: Reactive Threshold Orchestration
Implements Equation 1 from technical problem statement:
a(t) = f(S(t)) if S(t) >= theta else a(t-1)
Acts only after network latency or packet loss breaches predetermined thresholds.
"""

from typing import Dict, List, Any

class ReactiveThresholdScheduler:
    def __init__(
        self,
        r_max_mbps: float = 100.0,
        latency_threshold_ms: float = 45.0,
        loss_threshold: float = 0.02,
        cooldown_steps: int = 2
    ):
        self.r_max_mbps = r_max_mbps
        self.latency_threshold_ms = latency_threshold_ms
        self.loss_threshold = loss_threshold
        self.cooldown_steps = cooldown_steps
        self.last_reconfig_step = -100
        self.previous_allocation: Dict[str, float] = {}
        self.reconfiguration_count = 0
        self.name = "Reactive Threshold"

    def allocate(
        self,
        active_robot_ids: List[str],
        current_state: List[float],
        flow_metrics: Dict[str, Any] = None,
        step: int = 0
    ) -> Dict[str, float]:
        """
        Checks if S(t) >= theta. If triggered, reallocates capacity to congested robots.
        Otherwise, maintains previous allocation a(t) = a(t-1).
        """
        n = len(active_robot_ids)
        if n == 0:
            return {}

        # Default uniform allocation if no previous state
        if not self.previous_allocation or set(self.previous_allocation.keys()) != set(active_robot_ids):
            uniform = self.r_max_mbps / n
            self.previous_allocation = {rid: uniform for rid in active_robot_ids}

        # Check thresholds on S(t) = [L(t), J(t), P_L(t), U(t)]
        latency_breached = current_state[0] >= self.latency_threshold_ms
        loss_breached = current_state[2] >= self.loss_threshold
        threshold_crossed = latency_breached or loss_breached

        # Check cooldown to prevent excessive oscillation
        can_reconfigure = (step - self.last_reconfig_step) >= self.cooldown_steps

        if threshold_crossed and can_reconfigure and flow_metrics:
            # Reconfigure reactively: find robots with high latency / loss and boost them
            self.reconfiguration_count += 1
            self.last_reconfig_step = step

            congested_robots = []
            healthy_robots = []
            for rid in active_robot_ids:
                flow = flow_metrics.get(rid, {})
                f_lat = flow.get("tail_p95_latency_ms", 0.0)
                f_loss = flow.get("packet_loss_ratio", 0.0)
                if f_lat >= self.latency_threshold_ms or f_loss >= self.loss_threshold:
                    congested_robots.append(rid)
                else:
                    healthy_robots.append(rid)

            if congested_robots and healthy_robots:
                # Give congested robots 1.8x share, remaining to healthy robots
                boost_weight = 1.8
                total_weights = len(congested_robots) * boost_weight + len(healthy_robots) * 1.0
                base_share = self.r_max_mbps / total_weights

                new_alloc = {}
                for rid in congested_robots:
                    new_alloc[rid] = base_share * boost_weight
                for rid in healthy_robots:
                    new_alloc[rid] = base_share * 1.0

                self.previous_allocation = new_alloc
                return new_alloc

        # If threshold not crossed or cooldown active, maintain previous allocation a(t-1)
        return self.previous_allocation.copy()
