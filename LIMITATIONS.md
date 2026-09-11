# Limitations & Scientific Scope

To maintain rigorous scientific honesty, this living document tracks all assumptions, abstractions, and known limitations of the CogniNet-6G framework.

---

## 1. Simulation vs. Real 6G Hardware Discrepancies
- **Simulation Environment:** The validation framework couples ns-3 with ROS2/Gazebo in WSL2. 
- **RF Channel Realism:** While ns-3 provides high-fidelity packet-level simulation, it abstracts complex physical sub-terahertz or mmWave phenomena (e.g., dynamic spatial blockage from metallic factory machinery, atmospheric absorption, hardware nonlinearities).
- **Protocol Stacks:** 6G standardization is ongoing; ns-3 models reflect 5G-NR Release 16/17 extensions configured with projected 6G parameters (1 ms subframe, high-bandwidth carriers) rather than finalized 3GPP 6G specifications.

## 2. Prediction Model Boundaries
- **Out-of-Distribution Dynamics:** The LSTM and Transformer predictors are trained on synthesized operational patterns (normal, inspection burst, convergence). Unprecedented failure modes (e.g., sudden simultaneous hardware failure of multiple base stations) will degrade forecasting accuracy, causing transient fallback to reactive performance.
- **Lookahead Tradeoff:** Increasing forecast horizon $\Delta$ expands reaction lead-time but amplifies prediction variance ($\text{MSE}$).

## 3. Semantic Prioritization Bounds
- **Synthetic Metadata Labels:** Because standardized industrial 6G semantic packet headers do not yet exist, message metadata is generated synthetically based on industrial robot application categories.
- **Classification Latency Budget:** Semantic inference must execute within the per-packet ingress pipeline without adding queuing delay greater than the latency savings it delivers.

## 4. Edge Computational Constraints
- **Resource Competition:** Running inference for three models (predictor, classifier, PPO policy) alongside Gazebo and ns-3 creates local compute contention. The edge deployment module (`160`) explicitly benchmarks inference latency against control interval $\Delta t$.
