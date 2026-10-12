"""
High-Legibility Patent-Grade System Architecture Diagram Generator for CogniNet-6G
Optimized for Springer Nature / IEEE Transactions Journals
Key Improvements:
1. Compact vertical aspect ratio (16.0" x 7.0") -> fits perfectly in two-column layouts without crowding text.
2. Large, high-contrast, crystal-clear typography (11.5 pt titles, 9.8 pt subtitles, 8.8 pt specifications).
3. 10 clearly delineated numbered modules with pastel fills matching the author's reference template.
4. 100% strictly orthogonal (Manhattan) dataflow routing with zero crossing or diagonal lines.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch

PAPER_FIG_DIR = r"E:\cogninet-6g\paper\figures"
os.makedirs(PAPER_FIG_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "DejaVu Serif", "Times", "Liberation Serif"],
    "font.size": 9.5,
    "figure.dpi": 300,
    "text.usetex": False
})

def generate_crystal_clear_architecture():
    # Width = 16.0 inches, Height = 7.0 inches (Compact aspect ratio ~ 2.3:1)
    fig = plt.figure(figsize=(16.0, 7.2), dpi=300)
    ax = fig.add_subplot(111)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    fig.patch.set_facecolor("#ffffff")

    # High-contrast color palette matching user reference template
    c_blue_fill = "#eef4ff"       # Crisp pastel lavender/blue
    c_blue_stroke = "#1e40af"     # Deep royal blue border
    c_green_fill = "#ecfdf5"      # Crisp pastel mint/green
    c_green_stroke = "#15803d"    # Forest green border
    c_gray_fill = "#f9fafb"       # Clean neutral grey
    c_gray_stroke = "#374151"     # Dark charcoal border
    c_red_fill = "#fef2f2"        # Crisp pastel rose
    c_red_stroke = "#b91c1c"      # Deep crimson border
    c_amber_fill = "#fffbeb"      # Crisp pastel amber/cream
    c_amber_stroke = "#b45309"    # Deep bronze/amber border

    arrow_col = "#1f2937"         # Dark slate for sharp arrows
    txt_dark = "#111827"          # Near-black for maximum contrast and legibility

    def draw_module_box(x, y, w, h, fill, stroke, title, subtitle, specs, stroke_w=1.6):
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.6",
                             facecolor=fill, edgecolor=stroke, linewidth=stroke_w, zorder=2)
        ax.add_patch(box)

        # 1. Module Title (Large, Bold Serif, High-Contrast Stroke Color)
        ax.text(x + w/2.0, y + h - 2.8, title, fontsize=11.2, fontweight="bold",
                ha="center", va="center", color=stroke, zorder=3)
        
        # 2. Subtitle / Architecture Component (Semi-Bold Dark Text)
        ax.text(x + w/2.0, y + h - 6.0, subtitle, fontsize=9.6, fontweight="bold",
                ha="center", va="center", color=txt_dark, zorder=3)
        
        # 3. High-Impact Technical Specifications (Sharp, Bold, Legible Lines)
        curr_y = y + h - 9.4
        for line in specs:
            ax.text(x + w/2.0, curr_y, line, fontsize=8.6,
                    ha="center", va="center", color=txt_dark, zorder=3)
            curr_y -= 3.0

    # =========================================================================
    # ROW 1 (TOP): FLEET SENSING, 6G RADIO CHANNEL & ZERO-COPY IPC BUFFER
    # y = 69.0 to 92.0 (Height = 23.0)
    # =========================================================================
    # Module 1: Industrial Robot Fleet
    draw_module_box(
        x=2.5, y=69.0, w=27.0, h=23.0,
        fill=c_blue_fill, stroke=c_blue_stroke,
        title="Module 1: Industrial Robot Fleet",
        subtitle="10 AMRs / AGVs (ROS 2 & Gazebo)",
        specs=[
            "• ISO 3691-4 E-Stop Alert: 100 Hz (URLLC)",
            "• Visual Odometry & Kinematics: 50 Hz",
            "• Inspection Video Telemetry: 10 Mbps (eMBB)"
        ]
    )

    # Module 2: 3GPP 6G mmWave InF Radio Channel
    draw_module_box(
        x=36.5, y=69.0, w=27.0, h=23.0,
        fill=c_blue_fill, stroke=c_blue_stroke,
        title="Module 2: 3GPP 6G mmWave Channel",
        subtitle="InF-DH Discrete-Event Model (ns-3)",
        specs=[
            "• 28 GHz Carrier, 100 MHz BW, 132 PRBs (mu=3)",
            "• Metallic Shadowing & Spatial Clutter Blockage",
            "• Real-Time CQI / RSRP / SINR Matrix Feedback"
        ]
    )

    # Module 3: Zero-Copy Shared-Memory Ring Buffer
    draw_module_box(
        x=70.5, y=69.0, w=27.0, h=23.0,
        fill=c_gray_fill, stroke=c_gray_stroke,
        title="Module 3: Zero-Copy IPC Buffer",
        subtitle="Lockless /dev/shm Ring Buffer",
        specs=[
            "• Atomic Lockless Telemetry Ring Buffer",
            "• Monotonic Sequence Counters (< 12 us Overhead)",
            "• Microsecond Multi-Rate Clock Realignment"
        ]
    )

    # =========================================================================
    # ROW 2 (MIDDLE): DIGITAL TWIN SYNCHRONIZER & DUAL-PATH PREDICTIVE/SEMANTIC AI
    # y = 37.0 to 59.0 (Height = 22.0)
    # =========================================================================
    # Module 4: Digital Twin State Synchronizer
    draw_module_box(
        x=2.5, y=37.0, w=27.0, h=22.0,
        fill=c_green_fill, stroke=c_green_stroke,
        title="Module 4: Digital Twin Synchronizer",
        subtitle="Rolling State Window W = 10 (5.0 s)",
        specs=[
            "• Real-Time Cyber-Physical Synchronization",
            "• Telemetry Despiking & Missing Frame Imputation",
            "• Bounded State Drift: Drift Delta < 0.0031"
        ]
    )

    # Module 5: Bi-LSTM QoS Demand Forecaster
    draw_module_box(
        x=36.5, y=37.0, w=27.0, h=22.0,
        fill=c_gray_fill, stroke=c_gray_stroke,
        title="Module 5: Bi-LSTM QoS Forecaster",
        subtitle="Lookahead Horizon H = 2.0 s (5 Steps)",
        specs=[
            "• 2-Layer Bi-LSTM (128 Hidden), 1.15 ms Inference",
            "• Predicts Fading: [RSRP, CQI, Latency, Loss]",
            "• Anticipates Shadowing Blockage 2.0 s in Advance"
        ]
    )

    # Module 6: Semantic Packet Ingress Classifier
    draw_module_box(
        x=70.5, y=37.0, w=27.0, h=22.0,
        fill=c_blue_fill, stroke=c_blue_stroke,
        title="Module 6: Semantic Ingress Classifier",
        subtitle="4-Tier Priority Engine (3-Layer MLP)",
        specs=[
            "• 4 Tiers: Alert (T1), Nav (T2), Tele (T3), Video (T4)",
            "• 100.0% Recall on Safety-Critical Packets",
            "• Sub-Millisecond Header Parsing: 0.28 ms (278 us)"
        ]
    )

    # =========================================================================
    # ROW 3 (BOTTOM): STATE CONSTRUCTOR, SAFE RL SLICER & O-RAN ACTUATION
    # y = 5.0 to 26.5 (Height = 21.5)
    # Width = 21.3 each, spacing = 3.6
    # x: [2.5, 27.4, 52.3, 76.2] -> 76.2 + 21.3 = 97.5
    # =========================================================================
    # Module 7: Cyber-Physical State Constructor
    draw_module_box(
        x=2.5, y=5.0, w=21.3, h=21.5,
        fill=c_gray_fill, stroke=c_gray_stroke,
        title="Module 7: State Constructor",
        subtitle="State Vector x(t) in R^36",
        specs=[
            "• Fuses [S_DT, S_pred, w_i, a(t-1)]",
            "• Multi-Modal Feature Normalization",
            "• Assembly Latency: 0.12 ms"
        ]
    )

    # Module 8: Constrained PPO Slicing Engine
    draw_module_box(
        x=27.4, y=5.0, w=21.3, h=21.5,
        fill=c_gray_fill, stroke=c_gray_stroke,
        title="Module 8: Constrained PPO",
        subtitle="Actor-Critic Slicing Agent",
        specs=[
            "• Continuous PRB Slice Quotas",
            "• Churn Penalty (lambda = 50.0)",
            "• Suppresses Reconfiguration Thrash"
        ]
    )

    # Module 9: Deterministic Convex Safety Projection
    draw_module_box(
        x=52.3, y=5.0, w=21.3, h=21.5,
        fill=c_red_fill, stroke=c_red_stroke,
        title="Module 9: Safety Projection",
        subtitle="KKT Operator Pi_C",
        specs=[
            "• Hard Invariant: a_URLLC >= 0.20",
            "• Closed-Form Convex Projection",
            "• 0.00% Safety SLA Violations"
        ]
    )

    # Module 10: O-RAN Near-RT RIC Actuator
    draw_module_box(
        x=76.2, y=5.0, w=21.3, h=21.5,
        fill=c_amber_fill, stroke=c_amber_stroke,
        title="Module 10: O-RAN Actuator",
        subtitle="E2-SM Slicing Interface",
        specs=[
            "• Dynamic PRB Slice Reallocation",
            "• Proportional Fair Subcarrier Sched.",
            "• Total Loop Budget: 2.82 ms (< 10 ms)"
        ]
    )

    # =========================================================================
    # HIGH-CONTRAST ORTHOGONAL (MANHATTAN) ROUTING & ANNOTATIONS
    # =========================================================================
    def draw_manhattan_arrow(points, label="", label_pos=(0, 0), label_ha="center", label_va="center", is_bidirectional=False):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        ax.plot(xs, ys, color=arrow_col, lw=1.5, zorder=4)

        if is_bidirectional:
            p_first, p_sec = points[0], points[1]
            p_penult, p_last = points[-2], points[-1]
            ax.annotate("", xy=p_last, xytext=p_penult,
                        arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5, mutation_scale=12),
                        zorder=5)
            ax.annotate("", xy=p_first, xytext=p_sec,
                        arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5, mutation_scale=12),
                        zorder=5)
        else:
            p_penult, p_last = points[-2], points[-1]
            ax.annotate("", xy=p_last, xytext=p_penult,
                        arrowprops=dict(arrowstyle="-|>", color=arrow_col, lw=1.5, mutation_scale=12),
                        zorder=5)

        if label:
            ax.text(label_pos[0], label_pos[1], label, fontsize=8.2, fontweight="bold",
                    color=txt_dark, ha=label_ha, va=label_va, zorder=6,
                    bbox=dict(boxstyle="square,pad=0.2", facecolor="#ffffff", edgecolor="#d1d5db", lw=0.6, alpha=0.96))

    # 1. Module 1 <-> Module 2 (Bidirectional 28 GHz mmWave Link)
    draw_manhattan_arrow(
        [(29.5, 80.5), (36.5, 80.5)],
        label="28 GHz mmWave Link", label_pos=(33.0, 82.5),
        is_bidirectional=True
    )

    # 2. Module 2 -> Module 3 (Radio CQI / RSRP Reports)
    draw_manhattan_arrow(
        [(63.5, 80.5), (70.5, 80.5)],
        label="CQI / RSRP Reports", label_pos=(67.0, 82.5)
    )

    # 3. Module 1 -> Module 3 (Top Bypass: Robot Odometry & Sensor Telemetry)
    draw_manhattan_arrow(
        [(16.0, 92.0), (16.0, 96.5), (84.0, 96.5), (84.0, 92.0)],
        label="Kinematic Odometry & High-Speed Ingress Streams (100 Hz)",
        label_pos=(50.0, 97.8)
    )

    # 4. Module 3 -> Module 6 (Direct Vertical Downward Arrow)
    draw_manhattan_arrow(
        [(84.0, 69.0), (84.0, 59.0)],
        label="Ingress Headers", label_pos=(84.8, 64.0), label_ha="left"
    )

    # 5. Module 3 -> Module 4 (Zero-Copy Telemetry Stream across corridor y=64.0)
    draw_manhattan_arrow(
        [(73.0, 69.0), (73.0, 64.0), (16.0, 64.0), (16.0, 59.0)],
        label="Zero-Copy Telemetry Stream (/dev/shm)",
        label_pos=(44.5, 65.4)
    )

    # 6. Module 4 -> Module 5 (Historic State Window W=10)
    draw_manhattan_arrow(
        [(29.5, 48.0), (36.5, 48.0)],
        label="Window W = 10", label_pos=(33.0, 49.8)
    )

    # 7. Module 5 -> Module 7 (Predicted Demand State S_pred across corridor y=32.5)
    draw_manhattan_arrow(
        [(50.0, 37.0), (50.0, 32.5), (8.5, 32.5), (8.5, 26.5)],
        label="Predicted State S_pred(t+H)",
        label_pos=(29.0, 34.0)
    )

    # 8. Module 6 -> Module 7 (Semantic Urgency Weights w_i across corridor y=29.5)
    draw_manhattan_arrow(
        [(78.0, 37.0), (78.0, 29.5), (17.5, 29.5), (17.5, 26.5)],
        label="Urgency Weights w_i in [0.1, 1.0]",
        label_pos=(54.0, 31.0)
    )

    # 9. Module 7 -> Module 8 (State Vector x(t))
    draw_manhattan_arrow(
        [(23.8, 15.7), (27.4, 15.7)],
        label="x(t)", label_pos=(25.6, 17.3)
    )

    # 10. Module 8 -> Module 9 (Candidate Action a_raw(t))
    draw_manhattan_arrow(
        [(48.7, 15.7), (52.3, 15.7)],
        label="a_raw(t)", label_pos=(50.5, 17.3)
    )

    # 11. Module 9 -> Module 10 (Safe Action a*(t))
    draw_manhattan_arrow(
        [(73.6, 15.7), (76.2, 15.7)],
        label="a*(t)", label_pos=(74.9, 17.3)
    )

    # 12. Module 10 -> Closed-Loop Feedback across bottom and left margin
    draw_manhattan_arrow(
        [(86.8, 5.0), (86.8, 1.5), (1.0, 1.5), (1.0, 80.5), (2.5, 80.5)],
        label="Closed-Loop E2-SM PRB Slice Quota Updates & State Feedback S(t+1), Reward r(t)",
        label_pos=(44.0, 2.8)
    )

    # Save at 300 DPI PNG and vector PDF
    png_path = os.path.join(PAPER_FIG_DIR, "fig1_system_architecture.png")
    pdf_path = os.path.join(PAPER_FIG_DIR, "fig1_system_architecture.pdf")
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"[+] Crystal-clear architecture diagram successfully generated:")
    print(f"    PNG: {png_path}")
    print(f"    PDF: {pdf_path}")

if __name__ == "__main__":
    generate_crystal_clear_architecture()
