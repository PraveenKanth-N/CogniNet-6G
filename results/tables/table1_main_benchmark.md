# Table 1: Overall Empirical Benchmark Comparison

| Scheduler | Mean Latency (ms) | P95 Latency (ms) | Jitter (ms) | Packet Loss (%) | SLA Violation Rate (%) | Critical Latency (ms) | Reconfig Cost |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **CogniNet-6G (Ours)** | 4.18 ± 6.02 | 10.18 ± 16.64 | 6.70 ± 12.03 | 24.76% | 1.70% | 0.53 ± 1.22 | 0.0403 |
| **Prediction Only** | 4.10 ± 6.07 | 10.12 ± 16.70 | 5.56 ± 10.66 | 23.99% | 1.81% | 0.60 ± 1.32 | 0.0000 |
| **Reactive Threshold** | 4.10 ± 6.07 | 10.12 ± 16.70 | 5.56 ± 10.66 | 23.99% | 1.81% | 0.60 ± 1.32 | 0.0000 |
| **Semantic Only** | 3.12 ± 3.38 | 8.66 ± 15.28 | 4.94 ± 8.68 | 23.98% | 0.79% | 0.38 ± 0.80 | 0.1013 |
| **Static Slicing** | 4.10 ± 6.07 | 10.12 ± 16.70 | 5.56 ± 10.66 | 23.99% | 1.81% | 0.60 ± 1.32 | 0.0000 |