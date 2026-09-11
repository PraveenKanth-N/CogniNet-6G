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

## 6. Development Phases & Verification

- [x] **Phase 1: Environment & Scaffolding** (Directory tree, configs, Git, health checks)
- [x] **Phase 2: Robot & Network Simulation** (ROS2 fleet simulator + ns-3 mmWave 6G InF model)
- [x] **Phase 3: Telemetry & Digital Twin** (Module 100 acquisition & Module 110 sync manager)
- [x] **Phase 4: Baselines Benchmark** (Static slicing, reactive threshold, heuristic baselines)
- [x] **Phase 5: Traffic Prediction** (LSTM primary MSE 0.2166 + Transformer comparison)
- [x] **Phase 6: Semantic Intelligence** (Lightweight MLP 0.28ms, 100% critical recall)
- [x] **Phase 7: PPO Scheduler & Safety Layer** (Stable-Baselines3 PPO + deterministic projection)
- [x] **Phase 8: Full Closed-Loop Integration** (Algorithm 1 ClosedLoopOrchestrator + ActionHandler)
- [x] **Phase 9: Edge Deployment & Monitoring** (FastAPI REST API, InfluxDB/Prometheus exporter, Grafana)
- [x] **Phase 10: Empirical Experiments & Statistical Evaluation** (150 multi-seed benchmark trials)
- [x] **Phase 11: Ablation & Robustness Studies** (11 isolated conditions A0-A10 across Scenarios B, E, J)
- [x] **Phase 12: Publication Evidence Package** (6 figures at 300 DPI PNG+PDF, LaTeX+Markdown tables)

---

## 7. How to Reproduce All Results

```bash
# Activate dedicated virtual environment in WSL2
source /root/cogninet-env/bin/activate
cd /mnt/e/cogninet-6g

# 1. Run Complete Automated Test Suite (38 tests, 96% coverage)
pytest -v

# 2. Run Main 150-Trial Benchmark Across 10 Scenarios & 5 Schedulers
python evaluation/comparison.py

# 3. Run 11-Condition Systematic Ablation Study
python evaluation/ablations.py

# 4. Generate 6 Publication-Grade Figures (PNG 300 DPI & PDF)
python evaluation/generate_figures.py

# 5. Generate Publication LaTeX & Markdown Tables
python evaluation/generate_tables.py

# 6. Launch Real-Time Edge Microservice
uvicorn cogninet.edge_service.app:app --host 0.0.0.0 --port 8000
```

---

## 8. Scientific Integrity Notice

In compliance with rigorous scientific standards, **zero results are fabricated**. Every metric, figure, and table reported in this repository is directly reproducible from the raw empirical execution logs. All plots are rendered programmatically at 300 DPI directly into `results/figures/`.
