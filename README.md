# CogniNet-6G: An AI-Native Closed-Loop Digital Twin Framework for Predictive Semantic Network Orchestration in Private 6G Industrial Robot Networks

[![Course](https://img.shields.io/badge/Course-CSI3901%20TARP-blue.svg)](https://vit.ac.in)
[![Semester](https://img.shields.io/badge/Semester-Fall%202026--27-green.svg)](https://vit.ac.in)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Phase-1%20Environment%20%26%20Scaffolding-yellow.svg)]()

## 1. Project Overview

Autonomous mobile robots (AMRs) and automated guided vehicles (AGVs) depend heavily on reliable, low-latency wireless communication for deterministic industrial automation. In multi-robot private 6G deployments, uncoordinated bursty traffic causes severe network degradation—latency spikes, queue starvation, and packet drops. Conventional industrial network managers react only after QoS thresholds are breached, causing robotic stalls or safety hazards.

**CogniNet-6G** introduces an AI-native, closed-loop digital twin orchestration framework that:
1. **Predicts Near-Future Network Congestion:** Employs an LSTM/Transformer sequence model over rolling telemetry history $S(t-k), \dots, S(t)$ to forecast degradation $\hat{S}(t+\Delta)$ seconds ahead.
2. **Prioritizes Traffic Semantically:** Analyzes incoming message metadata (e.g., emergency stop vs. periodic battery telemetry) using a lightweight classifier to assign priority weights $w_i(t) \in [0, 1]$.
3. **Optimizes Dynamic Slicing & Scheduling via PPO:** Uses Proximal Policy Optimization to proactively reallocate bandwidth shares $\mathbf{a}(t)$ before congestion manifests.
4. **Guarantees Safety via Deterministic Constraints:** Applies an independent, hard safety override ($w_i(t) \ge w_{\text{crit}} \implies D_i(t) \le D_{\max}$) that cannot be overridden or softened by the reinforcement learning agent.
5. **Closes the Loop in a Synchronized Digital Twin:** Continuously updates a digital replica of both robotic fleet states and wireless network topologies with post-action telemetry feedback.

---

## 2. Research Team & Academic Context

- **Institution:** School of Computer Science and Engineering, Vellore Institute of Technology (VIT)
- **Course:** Technical Answers for Real World Problems (TARP), CSI3901
- **Semester:** Fall Semester 2026–27
- **Authors:**
  - **Dharma S** (Reg. No: 23MIC0104)
  - **Kishore B** (Reg. No: 23MIC0050)
  - **Praveen Kanth N** (Reg. No: 23MIC0078)

---

## 3. Architecture Blueprint

```text
[ Robot Fleet (ROS2/Gazebo) ]  <--->  [ Wireless Network (ns-3) ]
             |                                    |
             +--------------> [100 Telemetry] <---+
                                    |
                        [110 Digital Twin Sync]
                               /          \
                              v            v
                   [120 Traffic Predictor] [130 Semantic Priority]
                               \          /
                                v        v
                       [140 PPO Scheduler]
                                    |
                         [Candidate Allocation]
                                    |
                       [Deterministic Safety Layer]
                                    |
                        [150 Network Orchestration]
                                    |
                        [170 Closed-Loop Feedback]
                                    |
                        (Loop back to Digital Twin)
```

---

## 4. Module Map

| Module ID | Component Name | Role | Stack |
|---|---|---|---|
| **100** | Telemetry Acquisition | Ingests, normalizes, and filters robot & network metrics | Python, ROS2 API |
| **110** | Digital Twin Sync | State synchronization, history ring buffers, drift checks | Redis / In-memory, Python |
| **120** | Traffic Prediction | Time-series forecasting ($\hat{S}(t+\Delta)$) | PyTorch (LSTM / Transformer) |
| **130** | Semantic Priority | Message classification into priority $w_i(t) \in [0,1]$ | PyTorch (Lightweight MLP/CNN) |
| **140** | PPO Scheduler | Continuous resource allocation policy $\pi_\psi(x(t))$ | Stable-Baselines3, Gymnasium |
| **Safety**| Hard Safety Layer | Enforces $D_i(t) \le D_{\max}$ for $w_i(t) \ge w_{\text{crit}}$ | Deterministic Feasibility Layer |
| **150** | Network Orchestration | Translates action vectors to ns-3 slice & queue params | ns-3 C++ / Python bindings |
| **160** | Edge Deployment | Packaged low-latency inference microservices | FastAPI, Docker |
| **165** | Monitoring Display | Live telemetry and KPI visualization | InfluxDB, Grafana |
| **170** | Closed-Loop Feedback | Calculates rewards, validates state transitions, logs loop | Python |

---

## 5. Directory Structure

```text
cogninet-6g/
├── README.md                      # Project identity & specifications
├── LICENSE                        # Apache 2.0 license
├── CITATION.cff                   # Citation metadata
├── CONTRIBUTIONS.md               # Scientific contribution tracking
├── METHODOLOGY.md                 # Mathematical formulation & equations
├── LIMITATIONS.md                 # Living document of technical limitations
├── literature_matrix.yaml         # Traceability matrix across 30 papers
├── docker-compose.yml             # Redis, InfluxDB, Grafana services
├── requirements.txt               # Python package requirements
├── pyproject.toml                 # Package configuration
├── configs/                       # Simulation, model, baseline configs
├── cogninet/                      # Core modules (100-170 + safety)
├── sim/                           # ROS2 workspace and ns-3 models
├── datasets/                      # Raw, processed, and metadata datasets
├── training/                      # Training pipelines (predictor, classifier, PPO)
├── baselines/                     # Static slicing, reactive threshold, ablations
├── experiments/                   # Scenario drivers & experimental runners
├── evaluation/                    # Metrics, statistical tests, validation
├── visualization/                 # Programmatic journal-grade figure generation
├── results/                       # Empirical results (tables, raw logs, figures)
├── reports/                       # Research decision log & notes
├── scripts/                       # Environment verification & reproduction
└── tests/                         # Unit, integration, safety & regression tests
```

---

## 6. Development Phases

- [x] **Phase 1: Environment & Scaffolding** (Directory tree, configs, Git, health checks)
- [ ] **Phase 2: Robot & Network Simulation** (ROS2/Gazebo fleet + ns-3 network model)
- [ ] **Phase 3: Telemetry & Digital Twin** (Modules 100 & 110)
- [ ] **Phase 4: Baselines First** (Static slicing & Reactive threshold)
- [ ] **Phase 5: Traffic Prediction** (LSTM primary + Transformer comparison)
- [ ] **Phase 6: Semantic Intelligence** (Task metadata priority classifier)
- [ ] **Phase 7: PPO Scheduler & Safety Layer** (RL agent + hard constraint override)
- [ ] **Phase 8: Full Closed-Loop Integration** (Algorithm 1 end-to-end execution)
- [ ] **Phase 9: Edge Deployment & Monitoring** (Docker, FastAPI, Grafana)
- [ ] **Phase 10: Empirical Experiments & Statistical Evaluation** (Multi-seed evaluation)
- [ ] **Phase 11: Ablation & Robustness Studies** (10 ablation conditions & stress testing)
- [ ] **Phase 12: Publication Evidence Package** (Final figures, tables, reproducible reports)

---

## 7. Scientific Integrity Notice

In compliance with rigorous scientific standards, **zero results are fabricated**. Unrun experiments are strictly demarcated as `NOT MEASURED` or `EXPERIMENT NOT YET RUN`. All plots and tables are generated programmatically from raw experimental telemetry.
