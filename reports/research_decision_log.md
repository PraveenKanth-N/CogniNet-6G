# Research Decision Log

| Entry ID | Date | Module | Decision | Rationale | Impact | Alternatives Considered |
|---|---|---|---|---|---|---|
| DEC-001 | 2026-09-11 | Storage | Build all repository files, environments, and data strictly on Drive `E:\` | Host Drive `C:\` has 67 GB free, while Drive `E:\` has 122 GB free; prevents host root exhaustion during heavy builds. | All WSL distributions, virtual environments, and caches reside on `E:\`. | Building on `C:\Users\nivet` |
| DEC-002 | 2026-09-11 | Architecture | Decouple Safety Enforcement into a deterministic post-policy layer | A learned policy cannot mathematically guarantee zero violations under edge cases or adversarial rewards. | Hard constraint $w_i \ge w_{\text{crit}} \implies D_i \le D_{\max}$ strictly maintained regardless of PPO weights. | Pure reward penalty for safety violations |
| DEC-003 | 2026-09-11 | Semantic | Select lightweight MLP/CNN instead of heavy LLM/Transformer for inline prioritization | Sub-millisecond packet-level ingress latency is required in industrial real-time control loops. | Minimal inference latency (~0.1ms), low memory footprint. | BERT/Transformer-based semantic encoders |
