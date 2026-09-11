# Table 3: Micro-Latency Breakdown of Closed-Loop AI Modules

| Pipeline Module | Empirical Latency (ms) | Design Budget (ms) | Status |
| :--- | :---: | :---: | :---: |
| Telemetry Ingress & Glitch Filtering (Module 100) | 0.38 | < 1.0 | PASSED (< Budget) |
| Digital Twin State Synchronization (Module 110) | 0.24 | < 1.0 | PASSED (< Budget) |
| LSTM Demand Forecasting Inference (Module 120) | 1.25 | < 5.0 | PASSED (< Budget) |
| Semantic Priority Classification (Module 130) | 0.28 | < 1.0 | PASSED (< Budget) |
| PPO Policy Action Generation (Module 140) | 0.42 | < 2.0 | PASSED (< Budget) |
| Deterministic Safety Feasibility Projection (Module 160) | 0.05 | < 0.5 | PASSED (< Budget) |
| Action Dispatch & Actuation (Module 150) | 0.12 | < 0.5 | PASSED (< Budget) |
| Reward Computation & State Logging (Module 170) | 0.08 | < 0.5 | PASSED (< Budget) |
| **Total Closed-Loop Orchestration Cycle** | **2.82** | **< 50.0** | **PASSED (< Budget)** |