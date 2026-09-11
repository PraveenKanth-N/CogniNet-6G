"""
Multi-Objective Reward Function for PPO Schedulers
Implements Equation 6:
r(t) = -alpha*L(t) - beta*P_L(t) + eta*SLA(t) + zeta*U(t) - lambda*||a(t) - a(t-1)||
Deconstructs and logs every reward term individually.
"""

from typing import Dict, List, Any
from dataclasses import dataclass, asdict

@dataclass
class RewardBreakdown:
    total_reward: float
    latency_penalty: float
    loss_penalty: float
    sla_reward: float
    utilization_reward: float
    reconfiguration_penalty: float

class RewardCalculator:
    def __init__(
        self,
        alpha: float = 0.35,
        beta: float = 0.25,
        eta: float = 0.20,
        zeta: float = 0.10,
        lambda_reconfig: float = 0.10,
        max_latency_ref: float = 100.0
    ):
        self.alpha = alpha
        self.beta = beta
        self.eta = eta
        self.zeta = zeta
        self.lambda_reconfig = lambda_reconfig
        self.max_latency_ref = max_latency_ref

    def compute(
        self,
        system_state: List[float],             # S(t) = [L, J, P_L, U]
        sla_satisfied: bool,
        current_action: Dict[str, float],
        previous_action: Dict[str, float] = None,
        r_max: float = 100.0
    ) -> RewardBreakdown:
        latency = system_state[0]
        loss_ratio = system_state[2]
        utilization = system_state[3]

        # 1. Latency penalty normalized by max reference: -alpha * (L / L_ref)
        lat_norm = min(2.0, latency / self.max_latency_ref)
        lat_pen = -self.alpha * lat_norm

        # 2. Packet loss penalty: -beta * P_L
        loss_pen = -self.beta * min(1.0, max(0.0, loss_ratio))

        # 3. SLA satisfaction bonus: +eta if SLA met else 0.0
        sla_bonus = self.eta if sla_satisfied else 0.0

        # 4. Resource utilization reward: +zeta * U
        util_bonus = self.zeta * min(1.0, max(0.0, utilization))

        # 5. Reconfiguration thrashing penalty: -lambda * (Sum |a_i(t) - a_i(t-1)| / (2 * R_max))
        reconfig_pen = 0.0
        if previous_action is not None:
            rids = set(current_action.keys()).union(set(previous_action.keys()))
            l1_diff = sum(abs(current_action.get(r, 0.0) - previous_action.get(r, 0.0)) for r in rids)
            diff_norm = min(1.0, l1_diff / (2.0 * r_max))
            reconfig_pen = -self.lambda_reconfig * diff_norm

        total = lat_pen + loss_pen + sla_bonus + util_bonus + reconfig_pen

        return RewardBreakdown(
            total_reward=round(total, 5),
            latency_penalty=round(lat_pen, 5),
            loss_penalty=round(loss_pen, 5),
            sla_reward=round(sla_bonus, 5),
            utilization_reward=round(util_bonus, 5),
            reconfiguration_penalty=round(reconfig_pen, 5)
        )
