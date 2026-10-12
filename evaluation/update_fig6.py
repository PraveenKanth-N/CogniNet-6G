import os
import matplotlib.pyplot as plt
import numpy as np

plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10.5,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.dpi": 300
})

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.2, 4.4), gridspec_kw={'width_ratios': [1, 1.35]})

# (a) Execution Latency vs O-RAN 10ms Budget
labels_bar = ["CogniNet-6G\nEdge AI Loop", "O-RAN Near-RT\nRIC Budget"]
times_bar = [2.82, 10.00]
colors_bar = ["#10b981", "#ef4444"]

bars = ax1.bar(labels_bar, times_bar, color=colors_bar, width=0.40, edgecolor="#1f2937", linewidth=1.2)
ax1.set_ylabel("Execution Time (ms)", fontweight="bold")
ax1.set_title("(a) Execution Loop vs. 10 ms O-RAN Budget", fontweight="bold", pad=14)
ax1.set_ylim(0, 12)
ax1.grid(axis="y", linestyle="--", alpha=0.5)

# Text on top of bars
ax1.text(0, 2.82 + 0.4, "2.82 ms", ha="center", va="bottom", fontweight="bold", fontsize=11)
ax1.text(1, 10.00 + 0.4, "10.00 ms", ha="center", va="bottom", fontweight="bold", fontsize=11)

# Annotate margin
ax1.annotate("7.18 ms (71.8%) Headroom Margin", xy=(0, 3.8), xytext=(0.48, 7.0),
             arrowprops=dict(facecolor="#2563eb", shrink=0.08, width=1.5, headwidth=6),
             fontsize=9.5, fontweight="bold", color="#1e40af", ha="center",
             bbox=dict(boxstyle="round,pad=0.35", fc="#eff6ff", ec="#3b82f6", lw=1.2))

# (b) Micro-latency Breakdown
modules = [
    "Module 5: Bi-LSTM Forecaster (1.25 ms)",
    "Module 8: Constrained PPO (0.52 ms)",
    "Module 6: Semantic MLP (0.28 ms)",
    "Module 4: DT Synchronizer (0.26 ms)",
    "Modules 7 & 10: State/Actuator (0.26 ms)",
    "Modules 3, 9, Feedback: IPC/Safety (0.25 ms)"
]
latencies = [1.25, 0.52, 0.28, 0.26, 0.26, 0.25]
colors = ["#3b82f6", "#8b5cf6", "#ec4899", "#06b6d4", "#f59e0b", "#10b981"]
explode = (0.04, 0.04, 0.04, 0.04, 0.04, 0.04)

wedges, texts, autotexts = ax2.pie(
    latencies,
    explode=explode,
    autopct="%1.1f%%",
    pctdistance=0.75,
    colors=colors,
    startangle=130,
    wedgeprops=dict(edgecolor="white", linewidth=1.5)
)

for autotext in autotexts:
    autotext.set_color("white")
    autotext.set_fontweight("bold")
    autotext.set_fontsize(9.5)

ax2.set_title("(b) Micro-Latency Breakdown by Module", fontweight="bold", pad=14)
ax2.legend(wedges, modules, title="Sub-Module Components", loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8.5, frameon=True)

plt.tight_layout(pad=1.8)

for out_dir in ["/mnt/e/cogninet-6g/results/figures", "/mnt/e/cogninet-6g/paper/figures"]:
    os.makedirs(out_dir, exist_ok=True)
    fig.savefig(os.path.join(out_dir, "fig6_runtime_timing_budget.png"), dpi=300, bbox_inches="tight")
    fig.savefig(os.path.join(out_dir, "fig6_runtime_timing_budget.pdf"), bbox_inches="tight")

print("Saved cleanly updated fig6_runtime_timing_budget.")
