# Mathematical Methodology & System Formulation

## 1. Mathematical Notation and Network Model

Let the robot fleet be represented by $R = \{r_1, r_2, \dots, r_N\}$, where $N$ is the number of active autonomous mobile robots (AMRs) or automated guided vehicles (AGVs).

The system operates over discrete control intervals $t \in \{0, 1, 2, \dots\}$ with time step $\Delta t$.

### Observable Network State Vector:
$$S(t) = \big[ L(t), J(t), P_L(t), U(t) \big]$$
where:
- $L(t) \in \mathbb{R}^+$ is the instantaneous / interval-average latency (ms).
- $J(t) \in \mathbb{R}^+$ is the network jitter (ms).
- $P_L(t) \in [0, 1]$ is the packet-loss ratio.
- $U(t) \in [0, 1]$ is the radio/slice resource utilization.

### Capacity Constraint:
$$\sum_{i=1}^N R_i(t) \le R_{\max}, \quad \forall t$$
where $R_i(t)$ is the allocated bandwidth or slice share for robot $r_i$, and $R_{\max}$ is the total available capacity.

---

## 2. Formulation of Subsystems

### 2.1 Reactive Baseline (Status Quo)
$$\mathbf{a}(t) = \begin{cases} f(S(t)), & \text{if } S(t) \ge \theta \\ \mathbf{a}(t-1), & \text{otherwise} \end{cases}$$
*Flaw:* Purely reactive step-function; cannot act until latency or packet loss has already degraded robot operation.

### 2.2 Traffic Prediction Module ($g_\theta$)
$$\hat{S}(t+\Delta) = g_\theta\big(S(t-k), S(t-k+1), \dots, S(t)\big)$$
Trained by minimizing mean squared forecasting error over historical sequence sequences:
$$\mathcal{L}_{\text{pred}}(\theta) = \frac{1}{|B|} \sum_{b \in B} \|\hat{S}_b(t+\Delta) - S_b(t+\Delta)\|^2$$

### 2.3 Semantic Importance Ranking Module ($h_\phi$)
$$w_i(t) = h_\phi(m_i(t)) \in [0, 1]$$
where $m_i(t)$ represents message metadata: task classification, urgency flag, message payload type, and safety criticality.

### 2.4 Scheduler Input Vector
$$\mathbf{x}(t) = \big[ \hat{S}(t+\Delta), \{w_i(t)\}_{i=1}^N \big]$$

### 2.5 Reinforcement Learning Policy ($\pi_\psi$)
Candidate allocation action:
$$\mathbf{a}_{\text{cand}}(t) = \pi_\psi(\mathbf{x}(t))$$
Optimized under the Proximal Policy Optimization (PPO) clipped objective:
$$J(\psi) = \mathbb{E}_t \left[ \min\left( \rho_t(\psi)\hat{A}_t, \, \text{clip}(\rho_t(\psi), 1-\epsilon, 1+\epsilon)\hat{A}_t \right) \right]$$

### 2.6 Multi-Objective Reward Function
$$r(t) = -\alpha L(t) - \beta P_L(t) + \eta \text{SLA}(t) + \zeta U(t) - \lambda \|\mathbf{a}(t) - \mathbf{a}(t-1)\|$$
where $\alpha, \beta, \eta, \zeta, \lambda > 0$ are hyperparameter weights balancing latency minimization, loss minimization, SLA compliance, efficient utilization, and policy stability.

### 2.7 Hard Safety Constraint Layer (Non-Negotiable)
$$\text{If } w_i(t) \ge w_{\text{crit}}, \quad \text{then } D_i(t) \le D_{\max}, \quad \forall t$$
If $\mathbf{a}_{\text{cand}}(t)$ violates the delay ceiling $D_{\max}$ for critical flows, the deterministic safety module projects $\mathbf{a}_{\text{cand}}(t)$ onto the safe feasible set:
$$\mathbf{a}(t) = \text{ProjectSafe}\big(\mathbf{a}_{\text{cand}}(t), \{w_i(t)\}_{i=1}^N, w_{\text{crit}}, D_{\max}\big)$$

---

## 3. Algorithm 1: CogniNet-6G Closed-Loop Orchestration

```
Algorithm 1: CogniNet-6G Closed-Loop Orchestration
Input: control interval Δt, forecast horizon Δ, trained predictor g_θ, trained classifier h_φ,
       trained policy π_ψ, safety threshold w_crit, maximum allowed delay D_max
Output: executed resource allocation a(t) at every control interval

1. Initialize digital twin state S(0) from first telemetry snapshot.
2. For each control interval t = 0, 1, 2, ...:
3.    Collect telemetry from robot fleet and wireless network; update S(t).
4.    Compute forecast Ŝ(t+Δ) = g_θ(S(t-k), ..., S(t)).
5.    For each active message m_i(t):
6.        Compute importance weight w_i(t) = h_φ(m_i(t)).
7.    Form scheduler input x(t) = [Ŝ(t+Δ), {w_i(t)}_{i=1}^N].
8.    Compute candidate allocation a_cand(t) = π_ψ(x(t)).
9.    Enforce deterministic hard safety constraint:
          a(t) = ProjectSafe(a_cand(t), {w_i(t)}, w_crit, D_max)
10.   Apply allocation a(t) to network slicing/scheduling layer.
11.   Observe resulting state S(t+1) after Δt; compute reward r(t).
12.   If training mode: update policy parameters ψ using PPO on r(t).
      If evaluation mode: record transition to experiment logs.
13.   Update digital twin state table: S(t) ← S(t+1).
14. End for
```
