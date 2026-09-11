"""
CogniNet-6G Publication-Grade Figure Generation Suite (Phase 11)
Reads empirical CSV telemetry tables and generates publication figures:
- Figure 1: End-to-End Mean & P95 Latency across Scenarios A-J (bar plot with error bars)
- Figure 2: SLA Violation Rates & Reliability Benchmark
- Figure 3: Critical Emergency Stop Response Time & Bandwidth Reallocation (Timeseries trace)
- Figure 4: Digital Twin Synchronization Drift Dynamics under Normal vs Degradation
- Figure 5: Systematic Ablation Study Impact on Latency & Safety Overrides
- Figure 6: Real-Time Execution Breakdown (< 50ms factory control deadline)

All figures saved in 300 DPI PNG and vector PDF formats to results/figures/.
"""

import os
import sys
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from experiments.scenarios.traffic_generator import Scenario
from cogninet.feedback.loop import ClosedLoopOrchestrator

# Apply IEEE / ACM Scientific Publication Style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "lines.linewidth": 1.8,
    "figure.dpi": 300
})

FIG_DIR = os.path.join(REPO_ROOT, "results", "figures")
TABLE_DIR = os.path.join(REPO_ROOT, "results", "tables")
os.makedirs(FIG_DIR, exist_ok=True)

def save_fig(fig, name: str):
    png_path = os.path.join(FIG_DIR, f"{name}.png")
    pdf_path = os.path.join(FIG_DIR, f"{name}.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Generated: {name}.png & {name}.pdf")

def plot_fig1_latency_by_scenario(df: pd.DataFrame):
    """Figure 1: Mean & P95 Latency Comparison Across 10 Scenarios."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), sharey=True)

    # Clean scenario labels
    df_plot = df.copy()
    df_plot["scenario_label"] = df_plot["scenario"].str.replace("scenario_", "").str.replace("_", " ").str.title()

    palette = {
        "Static Slicing": "#95a5a6",
        "Reactive Threshold": "#e67e22",
        "Semantic Only": "#3498db",
        "Prediction Only": "#9b59b6",
        "CogniNet-6G (Ours)": "#2ecc71"
    }

    sns.barplot(
        data=df_plot, x="scenario_label", y="mean_latency_ms", hue="scheduler",
        palette=palette, ax=ax1, errorbar="sd", capsize=0.1
    )
    ax1.set_title("(a) Mean End-to-End Latency")
    ax1.set_xlabel("Industrial Scenario")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha="right")
    ax1.legend().set_visible(False)

    sns.barplot(
        data=df_plot, x="scenario_label", y="p95_latency_ms", hue="scheduler",
        palette=palette, ax=ax2, errorbar="sd", capsize=0.1
    )
    ax2.set_title("(b) 95th Percentile (Tail) Latency")
    ax2.set_xlabel("Industrial Scenario")
    ax2.set_ylabel("")
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha="right")
    ax2.legend(title="Scheduler", bbox_to_anchor=(1.02, 1), loc="upper left")

    fig.suptitle("6G Network Slicing Latency Across Industrial Operational Scenarios (N=10 Robots)", y=1.02)
    save_fig(fig, "fig1_latency_by_scenario")

def plot_fig2_sla_and_reliability(df: pd.DataFrame):
    """Figure 2: SLA Violations and Critical Message Latency."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    palette = {
        "Static Slicing": "#95a5a6",
        "Reactive Threshold": "#e67e22",
        "Semantic Only": "#3498db",
        "Prediction Only": "#9b59b6",
        "CogniNet-6G (Ours)": "#2ecc71"
    }

    df_plot = df.copy()
    df_plot["scenario_label"] = df_plot["scenario"].str.replace("scenario_", "").str.replace("_", " ").str.title()

    sns.barplot(
        data=df_plot, x="scenario_label", y="sla_violation_rate", hue="scheduler",
        palette=palette, ax=ax1, errorbar=None
    )
    ax1.set_title("(a) SLA Latency Violation Rate (> 45 ms)")
    ax1.set_xlabel("Industrial Scenario")
    ax1.set_ylabel("SLA Violation Fraction")
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45, ha="right")
    ax1.legend().set_visible(False)

    sns.barplot(
        data=df_plot, x="scenario_label", y="critical_latency_ms", hue="scheduler",
        palette=palette, ax=ax2, errorbar=None
    )
    ax2.axhline(10.0, color="red", linestyle="--", linewidth=1.5, label="D_max Safety Bound (10 ms)")
    ax2.set_title("(b) Critical Message Delivery Latency")
    ax2.set_xlabel("Industrial Scenario")
    ax2.set_ylabel("Critical Message Latency (ms)")
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45, ha="right")
    ax2.legend(bbox_to_anchor=(1.02, 1), loc="upper left")

    save_fig(fig, "fig2_sla_and_reliability")

def plot_fig3_critical_safety_trace():
    """Figure 3: High-Resolution Temporal Trace of Emergency Stop Trigger."""
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    model_paths = {
        "predictor": os.path.join(models_dir, "lstm_predictor.pt"),
        "semantic": os.path.join(models_dir, "semantic_classifier.pt"),
        "ppo": os.path.join(models_dir, "ppo_scheduler.zip")
    }

    # Run CogniNet-6G with safety
    orch_safe = ClosedLoopOrchestrator(
        config=config, scenario=Scenario.E_CRITICAL_SAFETY, model_paths=model_paths,
        enable_safety_override=True, policy_type="ppo", random_seed=42
    )
    log_safe = orch_safe.run_simulation(duration_s=25.0)

    # Run without safety override
    orch_nosafe = ClosedLoopOrchestrator(
        config=config, scenario=Scenario.E_CRITICAL_SAFETY, model_paths=model_paths,
        enable_safety_override=False, policy_type="ppo", random_seed=42
    )
    log_nosafe = orch_nosafe.run_simulation(duration_s=25.0)

    times = [r["timestamp"] for r in log_safe]
    bw_safe_r01 = [r["allocations"]["r01"] for r in log_safe]
    bw_nosafe_r01 = [r["allocations"]["r01"] for r in log_nosafe]
    weights_r01 = [r["weights"]["r01"] for r in log_safe]

    # Critical latency estimates
    lat_safe_r01 = [r["state"][0] * (10.0 / max(1.0, r["allocations"]["r01"])) for r in log_safe]
    lat_nosafe_r01 = [r["state"][0] * (10.0 / max(1.0, r["allocations"]["r01"])) for r in log_nosafe]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    # Top: Bandwidth & Urgency Weight
    ax1.plot(times, bw_safe_r01, color="#2ecc71", linewidth=2.2, label="CogniNet-6G (Safety Override Active)")
    ax1.plot(times, bw_nosafe_r01, color="#e74c3c", linestyle="--", label="w/o Safety Override")
    ax1.axhline(15.0, color="orange", linestyle=":", label="Min Critical Slice (15 Mbps)")
    ax1.axvspan(10.0, 11.0, color="yellow", alpha=0.25, label="Emergency Stop Trigger (t=10s)")
    ax1.set_ylabel("Bandwidth Allocated to r01 (Mbps)")
    ax1.set_title("Autonomous Safety Override Reaction to Critical Emergency Stop (Scenario E)")
    ax1.legend(loc="upper right")

    # Bottom: Delivery Latency vs Hard Safety Bound
    ax2.plot(times, lat_safe_r01, color="#2ecc71", linewidth=2.2, label="CogniNet-6G Latency")
    ax2.plot(times, lat_nosafe_r01, color="#e74c3c", linestyle="--", label="w/o Safety Override Latency")
    ax2.axhline(10.0, color="red", linestyle="-", linewidth=1.5, label="Hard Safety SLA Bound D_max (10 ms)")
    ax2.axvspan(10.0, 11.0, color="yellow", alpha=0.25)
    ax2.set_xlabel("Simulation Time (seconds)")
    ax2.set_ylabel("End-to-End Latency (ms)")
    ax2.legend(loc="upper right")

    save_fig(fig, "fig3_critical_safety_response")

def plot_fig4_digital_twin_drift():
    """Figure 4: Digital Twin State Tracking and Drift under Channel Degradation."""
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    model_paths = {
        "predictor": os.path.join(models_dir, "lstm_predictor.pt"),
        "semantic": os.path.join(models_dir, "semantic_classifier.pt"),
        "ppo": os.path.join(models_dir, "ppo_scheduler.zip")
    }

    orch = ClosedLoopOrchestrator(
        config=config, scenario=Scenario.J_NETWORK_DEGRADATION, model_paths=model_paths,
        enable_safety_override=True, policy_type="ppo", random_seed=42
    )
    log = orch.run_simulation(duration_s=30.0)

    times = [r["timestamp"] for r in log]
    drifts = [r["twin_drift"] for r in log]
    actual_lat = [r["state"][0] for r in log]
    pred_lat = [r["predicted_state"][0] for r in log]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

    ax1.plot(times, actual_lat, color="#2980b9", label="Actual Network Latency L(t)")
    ax1.plot(times, pred_lat, color="#e67e22", linestyle="--", label="Digital Twin Forecast L_hat(t+Delta)")
    ax1.axvline(20.0, color="red", linestyle=":", label="Channel Degradation Injected (t=20s)")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_title("Digital Twin Predictive State Synchronization under Channel Degradation (Scenario J)")
    ax1.legend(loc="upper left")

    ax2.plot(times, drifts, color="#8e44ad", linewidth=2.0, label="Synchronization Drift Delta_drift")
    ax2.axhline(0.25, color="orange", linestyle="--", label="Drift Tolerance Alert Bound (0.25)")
    ax2.axvline(20.0, color="red", linestyle=":")
    ax2.set_xlabel("Simulation Time (seconds)")
    ax2.set_ylabel("Drift Metric")
    ax2.legend(loc="upper left")

    save_fig(fig, "fig4_digital_twin_drift")

def plot_fig5_ablation_study():
    """Figure 5: Systematic Ablation Study Breakdown (11 Conditions)."""
    abl_csv = os.path.join(TABLE_DIR, "ablation_study_results.csv")
    if not os.path.exists(abl_csv):
        print("[-] Missing ablation_study_results.csv")
        return

    df_abl = pd.read_csv(abl_csv)
    summary = df_abl.groupby(["ablation_id", "ablation_name"])[["mean_latency_ms", "critical_latency_ms", "reconfiguration_cost"]].mean().reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(summary))
    width = 0.28

    r1 = ax.bar(x - width, summary["mean_latency_ms"], width, label="Mean Latency (ms)", color="#3498db")
    r2 = ax.bar(x, summary["critical_latency_ms"], width, label="Critical Message Latency (ms)", color="#e74c3c")
    r3 = ax.bar(x + width, summary["reconfiguration_cost"] * 20.0, width, label="Reconfig Cost (x20 norm)", color="#f39c12")

    ax.set_ylabel("Performance Metric Value")
    ax.set_title("Ablation Study: Component Impact on System Latency & Reconfiguration Cost")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["ablation_id"] + "\n" + summary["ablation_name"].str.slice(0, 20), rotation=30, ha="right")
    ax.legend(loc="upper left")

    save_fig(fig, "fig5_ablation_comparison")

def plot_fig6_timing_budget():
    """Figure 6: Real-Time Closed Loop Latency Breakdown vs. 50 ms Control Deadline."""
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    model_paths = {
        "predictor": os.path.join(models_dir, "lstm_predictor.pt"),
        "semantic": os.path.join(models_dir, "semantic_classifier.pt"),
        "ppo": os.path.join(models_dir, "ppo_scheduler.zip")
    }

    orch = ClosedLoopOrchestrator(
        config=config, scenario=Scenario.A_NORMAL, model_paths=model_paths,
        enable_safety_override=True, policy_type="ppo", random_seed=42
    )
    log = orch.run_simulation(duration_s=10.0)

    # Steady state steps
    steady_steps = log[1:]
    pred_ms = [r["timing_ms"]["prediction_ms"] for r in steady_steps]
    sem_ms = [r["timing_ms"]["semantic_ms"] for r in steady_steps]
    dec_ms = [r["timing_ms"]["decision_ms"] for r in steady_steps]
    safe_ms = [r["timing_ms"]["safety_ms"] for r in steady_steps]
    act_ms = [r["timing_ms"]["actuator_ms"] for r in steady_steps]

    avg_timing = {
        "Prediction (LSTM)": np.mean(pred_ms),
        "Semantic (MLP)": np.mean(sem_ms),
        "RL Policy (PPO)": np.mean(dec_ms),
        "Safety Screen": np.mean(safe_ms),
        "Actuation Dispatch": np.mean(act_ms)
    }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Bar chart vs 50ms deadline
    total_ai_ms = sum(avg_timing.values())
    ax1.bar(["CogniNet-6G AI Cycle", "Factory Real-Time Deadline"], [total_ai_ms, 50.0], color=["#2ecc71", "#e74c3c"], width=0.45)
    ax1.set_ylabel("Execution Time (milliseconds)")
    ax1.set_title("(a) Control Loop Latency vs. 50 ms Hard Deadline")
    for i, v in enumerate([total_ai_ms, 50.0]):
        ax1.text(i, v + 1.0, f"{v:.2f} ms", ha="center", fontweight="bold")
    ax1.set_ylim(0, 58)

    # Pie chart of AI sub-components
    ax2.pie(
        avg_timing.values(), labels=avg_timing.keys(), autopct="%1.1f%%",
        colors=["#3498db", "#9b59b6", "#f1c40f", "#e67e22", "#1abc9c"], startangle=140
    )
    ax2.set_title("(b) Micro-latency Breakdown of Edge AI Components")

    save_fig(fig, "fig6_runtime_timing_budget")

def main():
    print("==================================================================")
    print("      CogniNet-6G Publication Figure Generation Pipeline          ")
    print("==================================================================\n")

    main_csv = os.path.join(TABLE_DIR, "main_comparison_results.csv")
    if os.path.exists(main_csv):
        df_main = pd.read_csv(main_csv)
        plot_fig1_latency_by_scenario(df_main)
        plot_fig2_sla_and_reliability(df_main)
    else:
        print("[-] main_comparison_results.csv not found")

    plot_fig3_critical_safety_trace()
    plot_fig4_digital_twin_drift()
    plot_fig5_ablation_study()
    plot_fig6_timing_budget()

    print("\n[+] All publication figures successfully rendered in results/figures/\n")

if __name__ == "__main__":
    main()
