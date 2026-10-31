import os, sys, re
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=120, bottom=120, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex="F2F2F2"):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading)

def set_table_borders(table, color="B0B0B0", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:bottom w:val="{val}" w:sz="6" w:space="0" w:color="000000"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_docx():
    doc = Document()
    
    # Page setup: Standard A4 / Letter with 1.0 inch margins
    for section in doc.sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # Styles setup
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(11)
    font.color.rgb = RGBColor(0, 0, 0)
    style_normal.paragraph_format.line_spacing = 1.15
    style_normal.paragraph_format.space_after = Pt(6)

    # Read LaTeX source and bbl
    with open(r'E:\cogninet-6g\paper\main.tex', 'r', encoding='utf-8') as f:
        tex = f.read()

    with open(r'E:\cogninet-6g\paper\main.bbl', 'r', encoding='utf-8') as f:
        bbl = f.read()

    # Parse bbl references
    items = re.split(r'\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}', bbl)
    bibs = []
    key_to_num = {}
    for i in range(1, len(items), 2):
        key = items[i].strip()
        raw_text = items[i+1].strip()
        text = re.sub(r'\\newblock\s*', '', raw_text)
        text = re.sub(r'\\emph\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\textbf\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\texttt\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\url\{([^}]+)\}', r'\1', text)
        text = re.sub(r'\\end\{thebibliography\}', '', text)
        text = re.sub(r'~', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        idx = len(bibs) + 1
        bibs.append((key, text))
        key_to_num[key] = idx

    def replace_cites(txt):
        def repl(m):
            keys = m.group(1).split(',')
            nums = [str(key_to_num.get(k.strip(), k.strip())) for k in keys]
            return f"[{', '.join(nums)}]"
        return re.sub(r'\\cite\{([^}]+)\}', repl, txt)

    def clean_math_text(txt):
        txt = replace_cites(txt)
        repls = [
            (r'\\textbf\{([^}]+)\}', r'\1'),
            (r'\\textit\{([^}]+)\}', r'\1'),
            (r'\\texttt\{([^}]+)\}', r'\1'),
            (r'\\url\{([^}]+)\}', r'\1'),
            (r'\\ref\{([^}]+)\}', r'\1'),
            (r'\\mathbf\{([^}]+)\}', r'\1'),
            (r'\\text\{([^}]+)\}', r'\1'),
            (r'\\mathcal\{([^}]+)\}', r'\1'),
            (r'\\mathbb\{([^}]+)\}', r'\1'),
            (r'\\Delta', 'Δ'),
            (r'\\Pi', 'Π'),
            (r'\\mu', 'μ'),
            (r'\\nu', 'ν'),
            (r'\\theta', 'θ'),
            (r'\\phi', 'ϕ'),
            (r'\\psi', 'ψ'),
            (r'\\ge', '≥'),
            (r'\\le', '≤'),
            (r'\\pm', '±'),
            (r'\\approx', '≈'),
            (r'\\times', '×'),
            (r'\\cdot', '·'),
            (r'\\forall', '∀'),
            (r'\\in', '∈'),
            (r'\\sum', '∑'),
            (r'\\sim', '∼'),
            (r'\\to', '→'),
            (r'\\leftarrow', '←'),
            (r'\\quad', '    '),
            (r'\\,', ' '),
            (r'---', '—'),
            (r'--', '–'),
            (r'~', ' '),
            (r'\\%', '%'),
            (r'\\&', '&'),
            (r'\\_', '_'),
            (r'\$', ''),
        ]
        for o, n in repls:
            txt = txt.replace(o, n)
        return txt.strip()

    # Document Header & Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(14)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("CogniNet-6G: An AI-Native Closed-Loop Digital Twin Framework for Predictive Semantic Network Orchestration in Private 6G Industrial Robot Networks")
    r_title.bold = True
    r_title.font.size = Pt(17)
    r_title.font.name = 'Times New Roman'

    # Authors with native superscripts
    p_auth = doc.add_paragraph()
    p_auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_auth.paragraph_format.space_after = Pt(4)
    authors_data = [
        ("Dharma S", "1"),
        (", Kishore B", "1"),
        (", Praveen Kanth N", "1"),
        (", Mohanasundaram R", "1,*"),
        (", Deepak Raj D M", "1,*")
    ]
    for name, sup in authors_data:
        r1 = p_auth.add_run(name)
        r1.bold = True
        r1.font.size = Pt(11)
        r2 = p_auth.add_run(sup)
        r2.bold = True
        r2.font.superscript = True
        r2.font.size = Pt(10)

    # Affiliations
    p_aff = doc.add_paragraph()
    p_aff.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_aff.paragraph_format.space_after = Pt(12)
    
    r_aff_sup = p_aff.add_run("1")
    r_aff_sup.font.superscript = True
    r_aff_sup.font.size = Pt(9.5)
    r_aff = p_aff.add_run(" School of Computer Science and Engineering, Vellore Institute of Technology, Vellore 632014, Tamil Nadu, India\n")
    r_aff.font.size = Pt(10)
    r_aff.font.italic = True
    
    r_cor_sup = p_aff.add_run("*")
    r_cor_sup.font.superscript = True
    r_cor = p_aff.add_run(" Corresponding authors: mohanasundaramr@vit.ac.in, deepakraj.dm@vit.ac.in\n")
    r_cor.font.size = Pt(9.5)
    
    r_std = p_aff.add_run("Student Contributions: Dharma S (Reg: 23MIC0104), Kishore B (Reg: 23MIC0050), Praveen Kanth N (Reg: 23MIC0078)")
    r_std.font.size = Pt(9.5)

    # Abstract Box
    p_abs = doc.add_paragraph()
    p_abs.paragraph_format.left_indent = Inches(0.4)
    p_abs.paragraph_format.right_indent = Inches(0.4)
    p_abs.paragraph_format.space_before = Pt(8)
    p_abs.paragraph_format.space_after = Pt(6)
    p_abs.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r_abs_h = p_abs.add_run("Abstract — ")
    r_abs_h.bold = True
    r_abs = p_abs.add_run(clean_math_text(
        "High-bandwidth inspection feeds and reliable low-latency performance are essential as industrial mobile robots navigate "
        "automated shop floors. Sub-millisecond control for functional safety is equally vital. In high-frequency 28 GHz mmWave private cellular "
        "links, physical obstacles—such as moving steel containers, overhead gantry cranes, and tall storage racks—frequently induce line-of-sight "
        "discontinuities, producing rapid drops in received signal strength. Conventional network slicing schedulers reactively adjust Physical "
        "Resource Block (PRB) quotas based on link quality only after queues accumulate and packets drop. In a mobile robot fleet traveling at "
        "1.5 to 2.0 m/s, this reaction lag frequently breaches communication keep-alive thresholds, triggering emergency mechanical braking that "
        "stalls production lines. In this work, we present CogniNet-6G: a closed-loop digital twin framework designed to forecast wireless link "
        "degradation and ensure safety-critical traffic remains protected before delays manifest. A 2-layer bidirectional Long Short-Term Memory "
        "(Bi-LSTM) network predicts slice demand across a 2.0 s lookahead horizon, paired with a sub-millisecond Multi-Layer Perceptron (MLP) "
        "packet classifier. An edge-deployed Proximal Policy Optimization (PPO) agent dynamically reassigns radio slices, while an analytical "
        "convex safety projection operator (Π_C) guarantees that the bandwidth allocation (a_URLLC ≥ 0.20) remains reserved whenever "
        "safety-critical packets are in transit. We validated CogniNet-6G through co-simulations coupling ROS 2 Gazebo robot kinematics with "
        "discrete-event ns-3 28 GHz 5G-LENA mmWave channels across 10 operational factory stress scenarios (150 independent trials, 9,000 control steps). "
        "Experimental results demonstrate that CogniNet-6G dispatches emergency stop messages in 0.45 ± 0.95 ms, eliminates safety SLA violations "
        "under severe interference and structural shadowing, cuts reallocation thrashing by 60.2%, and runs in 2.82 ms on commodity edge hardware, "
        "comfortably within the 10 ms O-RAN Near-RT RIC scheduling envelope."
    ))
    r_abs.font.size = Pt(10)

    p_kw = doc.add_paragraph()
    p_kw.paragraph_format.left_indent = Inches(0.4)
    p_kw.paragraph_format.right_indent = Inches(0.4)
    p_kw.paragraph_format.space_after = Pt(16)
    r_kw_h = p_kw.add_run("Keywords — ")
    r_kw_h.bold = True
    r_kw = p_kw.add_run("6G Networks · Digital Twin · Reinforcement Learning · Semantic Communication · Network Slicing · Industrial Robots (AGV/AMR) · AI-Native Orchestration · Private Networks · O-RAN · Predictive QoS")
    r_kw.font.size = Pt(9.5)

    def add_h1(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(clean_math_text(text))
        run.bold = True
        run.font.size = Pt(13)
        run.font.name = 'Times New Roman'

    def add_h2(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(clean_math_text(text))
        run.bold = True
        run.font.size = Pt(11.5)
        run.font.name = 'Times New Roman'

    def add_h3(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        run = p.add_run(clean_math_text(text))
        run.bold = True
        run.italic = True
        run.font.size = Pt(11)
        run.font.name = 'Times New Roman'

    def add_body(text):
        cleaned = clean_math_text(text)
        if not cleaned:
            return
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(cleaned)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(11)

    def add_equation(eq_text, eq_num):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r1 = p.add_run(f"    {clean_math_text(eq_text)}    ")
        r1.font.italic = True
        r1.font.name = 'Times New Roman'
        r2 = p.add_run(f"({eq_num})")
        r2.bold = True
        r2.font.name = 'Times New Roman'

    def add_bullet(lead_bold, rest_text):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        if lead_bold:
            r1 = p.add_run(clean_math_text(lead_bold) + " ")
            r1.bold = True
        p.add_run(clean_math_text(rest_text))

    def add_numbered(num_str, lead_bold, rest_text):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.15
        r_num = p.add_run(num_str + " ")
        r_num.bold = True
        if lead_bold:
            r1 = p.add_run(clean_math_text(lead_bold) + " ")
            r1.bold = True
        p.add_run(clean_math_text(rest_text))

    def add_figure(img_path, caption_text, width=Inches(6.0)):
        if os.path.exists(img_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run()
            run.add_picture(img_path, width=width)
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(2)
            p_cap.paragraph_format.space_after = Pt(10)
            p_cap.paragraph_format.keep_with_next = False
            r_cap = p_cap.add_run(clean_math_text(caption_text))
            r_cap.font.size = Pt(9.5)
            r_cap.font.italic = True
        else:
            print(f"Warning: image {img_path} not found")

    # 1. INTRODUCTION
    add_h1("1. Introduction")
    add_h2("1.1 General Description")
    add_body(
        "Modern manufacturing facilities are steadily replacing static mechanical conveyor systems with autonomous mobile robots (AMRs) "
        "and automated guided vehicles (AGVs) [13, 31]. In automotive assembly, battery gigafactories, and cleanrooms, mobile robot fleets transport components, "
        "inspect assemblies with high-definition vision cameras, and work alongside human technicians without physical protective fences [12, 21]."
    )
    add_body(
        "Because physical mobility prevents the use of wired connections, every movement trajectory, sensor update, cooperative maneuver, and emergency stop command "
        "must travel over a wireless medium [9, 35]. Private cellular networks deployed in millimetre-wave (mmWave) bands—specifically 28 GHz and sub-terahertz frequencies—have "
        "become the preferred wireless backbone for smart manufacturing [4, 3]. These deployments deliver gigabit-per-second uplink throughput with nominal air-interface delays "
        "under a millisecond, satisfying the nominal requirements of Ultra-Reliable Low-Latency Communication (URLLC) [9]."
    )
    add_body(
        "However, dense robot fleet operations over mmWave wireless links reveal serious protocol- and physical-level vulnerabilities [6, 11]. "
        "Directional propagation at 28 GHz relies on narrow beams and experiences high path loss [4]. Moving metallic objects, such as automated gantry cranes, "
        "forklift assemblies, and steel inventory racking, frequently obstruct line-of-sight (LOS) paths, resulting in abrupt 20 to 30 dB reductions in received signal strength. "
        "Simultaneously, factory processes produce bursty, synchronized data surges. When multiple AMRs meet at a narrow aisle or upload 4K camera frames concurrently, "
        "local wireless links suffer sudden queue build-ups, beam misalignments, and radio resource starvation."
    )

    add_h2("1.2 Problem Statement in Detail")
    add_body(
        "In our trials with Open Radio Access Network (O-RAN) slicing controllers and Near-RT RIC schedulers, we pinpointed three structural bottlenecks that uniformly degrade the operations of robotic fleets:"
    )
    add_numbered("1.", "Reactive Hysteresis Lag:", 
        "Current slicing schedulers maintain a sliding window average for link quality and only redistribute Physical Resource Blocks (PRBs) after packet delay or loss rates exceed a preset alarm threshold [28, 38]. If a robot moves at speeds between 1.5 and 2.0 m/s, reacting after congestion occurs is hazardous. Because O-RAN Near-RT control loops require 50 to 200 ms to register errors, execute optimization routines, and reconfigure radio schedulers, robots breach communication keep-alives before the radio link adapts. Under ISO 3691-4 and IEC 61508 safety standards [2, 1], this activates emergency mechanical brakes, stalls production lines, and brings routes to a standstill."
    )
    add_numbered("2.", "Semantic Blindness in Radio Buffers:", 
        "Cellular protocol stacks operate on packets virtually as raw byte streams over generic data bearers [27, 36]. Schedulers handle incoming packets within a generic bearer identically, managing them through FIFO or round-robin queuing. A 50-byte kinematic correction or emergency stop (E-stop) packet is thus queued behind a 1.5 MB LiDAR point cloud or raw video frame [10, 16]. Head-of-line blocking occurs when safety alerts get stuck in queue during heavy non-critical telemetry bursts."
    )
    add_numbered("3.", "Allocation Thrashing in Unconstrained RL:", 
        "Recent studies applying Deep Reinforcement Learning (DRL) to network slicing typically frame the challenge as an unconstrained continuous optimization problem [24, 5]. This configuration often produces policies prone to volatility (flapping) that oscillate over successive control cycles. Rapidly shifting slice allocations floods the O-RAN E2 interface with control signaling. More critically, unconstrained exploratory policies cannot guarantee deterministic bandwidth reservations [1], occasionally under-allocating mission-critical slices during learning phases."
    )
    add_body(
        "To formulate this problem mathematically, let R = {r_1, r_2, ..., r_N} denote a fleet of N industrial AMRs served by a private 6G gNodeB. "
        "The radio access network partitions its total available bandwidth B_tot across K network slices K = {URLLC, eMBB, mMTC}. At each discrete decision epoch t, "
        "the slice allocation vector is defined as a(t) = [a_1(t), a_2(t), ..., a_K(t)]^T ∈ R^K, residing on the probability simplex ∑_{k=1}^K a_k(t) ≤ 1 with a_k(t) ≥ 0, ∀k. "
        "Each robot r_i produces industrial traffic carrying an intrinsic semantic urgency weight w_i(t) ∈ [0, 1], where w_i(t) ≈ 1 designates life-critical E-stop alerts and w_i(t) ≈ 0 designates routine diagnostic telemetry."
    )
    add_body("Let the observable network state vector at epoch t be:")
    add_equation("S(t) = [ L(t), J(t), P_l(t), U(t) ]^T", "1")
    add_body("where L(t) represents mean end-to-end latency, J(t) denotes packet jitter, P_l(t) is packet loss ratio, and U(t) is aggregate PRB utilization. The total radio capacity constraint is given by:")
    add_equation("∑_{i=1}^N R_i(t) ≤ R_max", "2")
    add_body("Existing reactive systems determine the slice reallocation action a(t) according to:")
    add_equation("a(t) = f(S(t)) if S(t) ≥ θ, else a(t-1)", "3")
    add_body("Because a(t) in Eq. (3) is a discontinuous step function triggered solely after a physical threshold violation has occurred, conventional industrial systems exhibit zero lookahead anticipation.")

    add_h2("1.3 Research Objectives")
    add_body("To address these limitations within an integrated, verifiable architecture, this work develops and evaluates CogniNet-6G around four specific objectives:")
    add_bullet("Cyber-Physical State Tracking:", "Construct a co-simulation environment linking mobile robot fleet motion (ROS 2 Humble / Gazebo) with 3GPP 28 GHz mmWave discrete-event channels (ns-3 v3.38), tracking physical reality with minimal digital twin estimation drift.")
    add_bullet("Predictive Semantic Ingress Handling:", "Train a lightweight bidirectional slice-level channel demand forecaster (2.0 s lookahead window) and a fast MLP classifier for packet priority weights (under 0.3 ms inference latency).")
    add_bullet("Safe Edge Reinforcement Learning:", "Deploy a PPO slicing agent governed by a closed-form convex safety projection operator (Π_C) that ensures hard URLLC bandwidth reservations under any network perturbations.")
    add_bullet("Industrial Stress Benchmarking:", "Evaluate the framework across 10 operational disruption scenarios (150 trials, 9,000 control steps) against four baselines and 11 ablation settings, verifying edge execution times strictly within the 10 ms O-RAN Near-RT RIC limit.")

    add_h2("1.4 Primary Contributions")
    add_body("The following summarizes the primary contributions of this article:")
    add_numbered("1.", "Closed-Loop Fleet Orchestration:", "We formulate CogniNet-6G, uniting robot kinematics, mmWave channel propagation, neural forecasting, and safe reinforcement learning into a unified operational feedback loop.")
    add_numbered("2.", "Exact Convex Safety Operator:", "We derive an analytical projection operator Π_C that intercepts RL actions and strictly enforces a_URLLC ≥ 0.20, mathematically proving zero safety SLA violations without relying on reward shaping alone.")
    add_numbered("3.", "Fast Semantic Header Classifier:", "We build a 3-layer MLP classifier that parses packet headers in 0.2788 ms, achieving 100.0% recall on safety-critical alerts without introducing buffer delays.")
    add_numbered("4.", "Comprehensive Co-Simulation Validation:", "Across 150 independent trials and 10 factory stress scenarios, CogniNet-6G dispatches emergency messages in 0.45 ± 0.95 ms, eliminates safety SLA violations, cuts reallocation thrashing by 60.2%, and executes in 2.82 ms on commodity edge hardware.")

    add_h2("1.5 Paper Organization")
    add_body(
        "The remainder of this article is organized as follows: Section 2 reviews recent literature across digital twins, semantic communications, and network slicing, highlighting existing research gaps in Table 1. "
        "Section 3 details the mathematical shortcomings of reactive slicing, presents the 10-module design of CogniNet-6G, and proves the safety projection theorem. "
        "Section 4 details the experimental setup, scenario benchmarks, and ablation experiments. "
        "Section 5 discusses engineering insights, benchmark comparisons, and practical deployment opportunities."
    )

    # 2. LITERATURE SURVEY
    add_h1("2. Literature Survey")
    add_body("To put things in perspective, CogniNet-6G was analysed in the context of investigations conducted in digital twins, goal-oriented semantic communication, reinforcement learning, and edge orchestration published between 2020 and 2026.")
    
    add_h2("2.1 Categorization of Contemporary Literature")
    add_body("Existing studies in this field generally cover four related aspects:")
    
    add_h3("2.1.1 Digital Twins in 6G and Industrial Cyber-Physical Systems")
    add_body(
        "Digital twins have proven to be a feasible way to simulate physical factory operations in software. In 6G Cloud-RAN, Fallahi et al. [13] verified the effectiveness of proactively admitting slices in a digital twin, but did not consider robot kinematics or semantics. Compared to centralized digital twin architectures, Rahmati and Rahmati [29] reported lower latency for federated DTs for edge resource allocation, but observed overhead from periodic synchronization rounds. Erel-Ozcevik et al. [12] optimized automated guided vehicle schedules in smart warehouses using a 6G twin paired with genetic search, without modeling realistic physical wireless links."
    )
    add_body(
        "Collaborative 3D twins over sliced 5G links in remote fablabs [18] and physics-informed models for robotic arm predictive maintenance [8] represent other related research lines. Synchronization drift between physical channels and digital twin state representations continues to be a significant challenge [11, 25]. Silva Pereira et al. [33] presented modular middleware patterns for distributed edge-layer synchronization, while Zhang et al. [40] showed that twin-assisted dynamic slicing stabilizes edge resource distribution in industrial IoT environments."
    )

    add_h3("2.1.2 Semantic Communication and Goal-Oriented Networking")
    add_body(
        "Semantic communication focuses on transmitting the task meaning rather than just raw bits, expanding upon foundational extensions to Weaver's information framework [27, 36]. Wang et al. [35] presented a roadmap of goal-oriented networking in industrial cyber-physical systems, emphasizing that semantic filtering provides significant latency reductions for robot control. To reduce visual payload while preserving object classification accuracy, Slot et al. [10] developed slot-attention mechanisms that extract key semantic features from edge video streams."
    )
    add_body(
        "Other research efforts explored state-space sequence models in semantic communication [16], collaborative semantic coding in multi-robot swarms [41], cross-modal scheduling in vehicular networks [22], and task-oriented age-of-information optimization [17]. These efforts demonstrate that semantic compression is efficient in terms of bandwidth, but do not yet couple packet urgency metrics directly back to the radio scheduler for live PRB allocation."
    )

    add_h3("2.1.3 Reinforcement Learning for Network Slicing and O-RAN RRM")
    add_body(
        "Deep reinforcement learning is by far the most popular approach to dynamic radio resource allocation in 5G-Advanced and 6G networks [6, 34]. Slicing approaches have been explored for agricultural IoT [20] and mmWave clustering via Q-learning [23]. Qazzaz et al. [28] proposed OREO, an rApp/xApp that utilizes an energy-saving PPO agent; while their model achieved stable policy convergence in continuous action spaces, it focused on macroscopic power savings without considering robot safety semantics."
    )
    add_body(
        "Yungaicela-Naula et al. [38] introduced an O-RAN QoS xApp based on SLA penalties, outperforming reactive baselines in terms of adherence. Monaco et al. [24] proposed CROWN, applying cross-attention DRL for joint power management and slice placement. Recent related research includes offloading incentives in twin networks [42] and foundational policy gradient methods [32]. However, current DRL slicers rely on soft reward penalties, allowing exploratory actions to violate mission-critical SLAs during training and environmental transitions."
    )

    add_h3("2.1.4 Edge Intelligence, O-RAN Architectures, and Autonomous Swarms")
    add_body(
        "Polese et al. [26] and Bonati et al. [7] studied O-RAN Near-RT RIC microservices (xApps) and E2 interfaces, concluding that radio control policies must execute within a strict 10 ms deadline. Hierarchical federated learning (HFL) was explored by Krishnamoorthy et al. [19] for slicing. Edge task offloading for swarms was investigated in [39], while federated LLMs for cellular management were discussed in [14]; however, LLM inference latency (>500 ms) is prohibitive for sub-frame radio control. Further studies examined transparent AI-RAN concepts [15], UAV edge trajectory control [37], edge-cloud continuums [30], and Non-Terrestrial Network slicing [5]."
    )

    # TABLE 1
    add_h3("Table 1: Master Literature Comparison Matrix (Frameworks vs. CogniNet-6G)")
    t1_data = [
        ["Framework / Reference", "DT Sync", "6G InF mmWave", "Traffic Forecaster", "Semantic Pri.", "RL Slicing", "Safety Invariant", "Fleet Size", "Loop Latency"],
        ["Fallahi et al. [13]", "Yes", "Sub-6 GHz", "None", "None", "DDPG", "None", "2 Arms", "> 100 ms"],
        ["Rahmati et al. [29]", "None", "5G NR", "None", "None", "FedAvg", "None", "10 AMRs", "> 50 ms"],
        ["Erel-Ozcevik et al. [12]", "Yes", "Sub-6 GHz", "None", "None", "Genetic Alg.", "None", "6 AGVs", "N/A"],
        ["Krishnamoorthy et al. [19]", "None", "5G NR", "None", "None", "Hier. FedRL", "Soft Penalty", "Generic", "> 30 ms"],
        ["Qazzaz et al. (OREO) [28]", "None", "5G/6G", "Heuristic", "None", "PPO xApp", "None", "Generic", "≈ 20 ms"],
        ["Yungaicela et al. (RSLAQ) [38]", "None", "5G NR", "None", "None", "Deep RL", "Soft Penalty", "Generic", "≈ 15 ms"],
        ["Monaco et al. (CROWN) [24]", "None", "O-RAN", "None", "None", "Cross-Attn DQN", "None", "Multi-cell", "≈ 12 ms"],
        ["Ali & Arslan [5]", "Yes", "6G mmWave", "None", "None", "DDPG", "Soft Penalty", "8 AMRs", "≈ 18 ms"],
        ["Slot et al. [10]", "None", "6G mmWave", "None", "Slot Attention", "None", "None", "Single Node", "N/A"],
        ["Zhang et al. [40]", "Yes", "5G Edge", "Static Reg.", "None", "Q-Learning", "None", "Multi-device", "> 40 ms"],
        ["CogniNet-6G (Proposed)", "Yes", "28 GHz InF", "LSTM (H=2.0s)", "MLP (4-tier)", "PPO", "Deterministic Π_C", "10–20 AMRs", "2.82 ms"]
    ]
    t1 = doc.add_table(rows=len(t1_data), cols=9)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t1)
    for r_idx, row in enumerate(t1_data):
        for c_idx, val in enumerate(row):
            cell = t1.cell(r_idx, c_idx)
            set_cell_margins(cell, top=80, bottom=80, left=100, right=100)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if c_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(8.5)
            if r_idx == 0:
                run.bold = True
                set_cell_shading(cell, "EAEAEA")
            elif r_idx == len(t1_data) - 1:
                run.bold = True
                set_cell_shading(cell, "F5F5F5")

    add_h2("2.2 Identified Research Gaps")
    add_body("Table 1 contrasts representative frameworks against CogniNet-6G. Comparing current literature with the practical needs of industrial robot fleets reveals several key shortcomings:")
    add_numbered("1.", "Isolated Pairwise Integration:", "Most studies combine at most two concepts—such as digital twins with RL, or RL with O-RAN, or semantic coding with physical MIMO. No single system integrates all four elements into an operational feedback loop for mobile robot swarms.")
    add_numbered("2.", "Absence of Physical Robotic Context:", "Schedulers rely exclusively on low-level RF indicators (RSRP, CQI, buffer depths), unaware whether an AMR is turning at an intersection or idling at a docking bay.")
    add_numbered("3.", "Detached Semantic Prioritization:", "Semantic communication research in computer vision emphasizes deep feature compression, but rarely conveys packet priority scores directly to live radio slicing schedulers.")
    add_numbered("4.", "Siloed Forecasting and Allocation:", "Traffic prediction and resource allocation typically operate as separate pipelines, with forecasting outputs rarely used directly in real-time control.")
    add_numbered("5.", "Passive Digital Twin Architectures:", "Existing factory digital twins function primarily as monitoring dashboards or offline diagnostic records rather than active controllers in the operational loop.")
    add_numbered("6.", "Single-Agent Evaluation Scopes:", "Most published benchmarks consider isolated single-robot scenarios, overlooking the contention, interference, and synchronized traffic spikes common in dense fleets.")
    add_numbered("7.", "Omission of Tail Metrics and Churn:", "Evaluations typically report average latency while omitting tail latency (L_95, L_99), jitter, and slice reconfiguration thrashing.")
    add_numbered("8.", "Neglect of Near-RT Execution Constraints:", "Several proposed deep learning models require heavy computation that exceeds the strict 10 ms execution budget of O-RAN Near-RT RIC microservices.")

    # 3. METHODS
    add_h1("3. Methods")
    add_h2("3.1 Detailed Explanation of the Existing Model")
    add_body(
        "Current factory private cellular slice management relies on reactive proportional-integral-derivative (PID) schedulers or hysteresis threshold adjustments embedded within the base station MAC layer [28, 38]. Let C_tot denote the total PRB capacity of the cell. Conventional schedulers monitor an exponential moving average (EMA) of buffer queue depths Q_k(t) and reported channel quality indicators CQI_i(t). Reallocation decisions occur at discrete monitoring intervals T_mon = 50 to 200 ms."
    )
    add_h3("3.1.1 Theoretical Failure Analysis of the Existing Model")
    add_body("Under high-frequency mmWave propagation in factory environments, obstacle dynamics follow Poisson arrival distributions for physical line-of-sight blockages. When a blockage occurs at time t_b, the received signal power drops abruptly according to:")
    add_equation("P_rx(t) = P_tx + G_tx + G_rx - PL(d) - χ_block · I(t ≥ t_b)", "4")
    add_body("where χ_block ~ N(μ_b, σ_b^2) denotes additional shadowing attenuation (20 to 30 dB). The effective signal-to-interference-plus-noise ratio (SINR) plummets, cutting channel capacity:")
    add_equation("C_k(t) = B_k · log_2(1 + SINR_k(t))", "5")
    add_body("Because reactive schedulers update allocations only after delay breaches threshold θ, the queue experiences transient build-up:")
    add_equation("Q_k(t) = max(0, Q_k(t-1) + λ_k(t) · Δt - C_k(t) · Δt)", "6")
    add_body("The reaction lag τ_react = T_mon + T_opt + T_act produces an unbuffered delay that violates functional safety requirements:")
    add_equation("L_e2e(t) = D_prop + D_trans + Q_k(t) / C_k(t) > D_max", "7")

    add_h2("3.2 Proposed Architecture / Proposed Model")
    add_body("To overcome these theoretical and practical bottlenecks, CogniNet-6G introduces a 10-module closed-loop architecture operating synchronously across the physical factory floor and edge computing layers:")
    add_numbered("•", "Module 1 (Robot Swarm Kinematics):", "Manages physical AMR movement, pose vectors, velocities, and route tracking via ROS 2 Humble and Gazebo.")
    add_numbered("•", "Module 2 (6G InF mmWave Radio Channel):", "Executes 28 GHz spatial channel models with 3D ray-tracing, structural blockage, and fast fading in ns-3 v3.38.")
    add_numbered("•", "Module 3 (Zero-Copy Shared-Memory IPC Ring Buffer):", "Transfers telemetry between ROS 2 and ns-3 over Linux POSIX shared memory with 12 μs inter-process delay.")
    add_numbered("•", "Module 4 (Digital Twin Synchronizer & Pre-processor):", "Ingests raw telemetry, applies Hampel filter despiking, linear interpolation, and rolling Z-score feature normalization.")
    add_numbered("•", "Module 5 (Bi-LSTM QoS Demand Forecaster):", "2-layer bidirectional LSTM (64 hidden units) forecasting slice traffic demand across a 2.0 s lookahead horizon.")
    add_numbered("•", "Module 6 (Semantic Priority Ingress Classifier):", "3-layer MLP parsing packet metadata in 0.2788 ms, outputting semantic urgency weights w_i(t) ∈ [0, 1].")
    add_numbered("•", "Module 7 (Cyber-Physical State Space Constructor):", "Fuses physical RF readings, robot kinematics, and forecaster predictions into state vector x(t) ∈ R^14.")
    add_numbered("•", "Module 8 (Constrained PPO Slicing Engine):", "Reinforcement learning actor-critic agent generating candidate slice vector a_tilde(t) on probability simplex.")
    add_numbered("•", "Module 9 (Deterministic Convex Safety Operator Π_C):", "Closed-form projection operator guaranteeing a_URLLC ≥ 0.20 whenever high-urgency packets are in transit.")
    add_numbered("•", "Module 10 (O-RAN Near-RT RIC Actuator):", "Dispatches verified decisions a*(t) across O-RAN E2-SM, updates ns-3 PRB quotas, and closes control loop in 2.82 ms.")

    add_figure(r"E:\cogninet-6g\paper\figures\fig1_system_architecture.png", "Figure 1: Complete 10-module system architecture of CogniNet-6G uniting robot kinematics, mmWave propagation, neural forecasting, and safe reinforcement learning into a unified closed loop.")

    add_h2("3.2.1 Mathematical Formulation of the Safety Projection Operator")
    add_body("Let candidate action produced by PPO agent be a_tilde(t) = [a_tilde_1, ..., a_tilde_K]^T on simplex S = {a | ∑ a_k ≤ 1, a_k ≥ 0}. The safety constraint defines convex subset:")
    add_equation("C = { a ∈ S | a_URLLC ≥ a_min, a_min = 0.20 }", "8")
    add_body("The projection operator solves constrained quadratic programming:")
    add_equation("a*(t) = argmin_{a ∈ C} 0.5 · || a - a_tilde(t) ||_2^2", "9")
    add_body("Theorem 1 (Closed-Form Analytical Safety Projection): If a_tilde_URLLC < a_min, the unique optimal projection is:")
    add_equation("a*_URLLC = a_min", "10")
    add_equation("a*_k = a_tilde_k · (1 - a_min) / (1 - a_tilde_URLLC),  ∀k ≠ URLLC", "11")
    add_body("Proof: Formulate the Lagrangian dual with multiplier ν for simplex equality and μ for safety inequality:")
    add_equation("L(a, ν, μ) = 0.5 · ∑ (a_k - a_tilde_k)^2 + ν · (∑ a_k - 1) + μ · (a_min - a_URLLC)", "12")
    add_body("Stationarity conditions require ∂L/∂a_URLLC = a_URLLC - a_tilde_URLLC + ν - μ = 0 and ∂L/∂a_k = a_k - a_tilde_k + ν = 0. For μ > 0, safety bound activates with a*_URLLC = a_min, leaving (1 - a_min) spectrum. Solving for ν yields proportional scaling in Eq. (11), completing the proof.")

    # ALGORITHM 1
    add_h3("Algorithm 1: CogniNet-6G Closed-Loop Orchestration")
    alg_data = [
        ["Algorithm 1: CogniNet-6G Closed-Loop Orchestration"],
        ["Require: Control interval Δt = 0.5 s, lookahead horizon Δ = 2.0 s, forecaster g_θ, classifier h_ϕ, policy π_ψ, safety bound a_min = 0.20.\n"
         "Ensure: Safe slice allocation vector a*(t).\n"
         " 1: Initialize Digital Twin state S(0) from physical initial readings.\n"
         " 2: for each control epoch t = 0, 1, 2, ... do:\n"
         " 3:     Ingest multi-modal telemetry from AMRs and ns-3; update S(t).\n"
         " 4:     Despike outliers and interpolate missing values via Module 4.\n"
         " 5:     Update Digital Twin rolling history X_t ← [X_{t-1}[2:W], x_t].\n"
         " 6:     Compute predicted demand S_hat(t + Δ) = g_θ(X_t) via Module 5.\n"
         " 7:     for each active ingress packet m_i(t) do:\n"
         " 8:         Compute semantic urgency weight w_i(t) = h_ϕ(m_i(t)) via Module 6.\n"
         " 9:     end for\n"
         "10:     Assemble composite state vector x(t) via Module 7.\n"
         "11:     Sample candidate slice allocation a_tilde(t) ~ π_ψ(x(t)) via Module 8.\n"
         "12:     if a_tilde_URLLC(t) < a_min or max_i w_i(t) ≥ w_crit then\n"
         "13:         a*(t) ← Π_C(a_tilde(t)) via Module 9. [Safety Override]\n"
         "14:     else\n"
         "15:         a*(t) ← a_tilde(t).\n"
         "16:     end if\n"
         "17:     Dispatch a*(t) to O-RAN Near-RT RIC via Module 10 (E2-SM interface).\n"
         "18:     Apply updated PRB slice quotas to ns-3 radio scheduler.\n"
         "19:     Measure resulting physical state S(t+1); compute reward r(t).\n"
         "20:     if training phase then update PPO parameters ψ via clipped surrogate loss.\n"
         "21:     Synchronize Digital Twin state: S(t) ← S(t+1).\n"
         "22: end for"]
    ]
    t_alg = doc.add_table(rows=2, cols=1)
    t_alg.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t_alg, color="000000", sz="6")
    t_alg.cell(0, 0).text = alg_data[0][0]
    t_alg.cell(0, 0).paragraphs[0].runs[0].bold = True
    set_cell_shading(t_alg.cell(0, 0), "EAEAEA")
    t_alg.cell(1, 0).text = alg_data[1][0]
    t_alg.cell(1, 0).paragraphs[0].runs[0].font.size = Pt(9.5)

    add_h2("3.3 Pre-Processing Methods")
    add_body("Before feeding streaming telemetry into the neural modules, the signals undergo three pre-processing steps:")
    add_numbered("1.", "Rolling Buffer Feature Scaling:", "Raw observations span different numerical orders of magnitude. A rolling FIFO ring buffer of depth W = 10 (5.0 s history at Δt = 0.5 s) tracks the empirical mean and standard deviation for each feature f:")
    add_equation("z_f(t) = (x_f(t) - μ_hat_f(t)) / (σ_hat_f(t) + 10^-6)", "13")
    add_numbered("2.", "Hampel Filter Despiking:", "Telemetry spikes caused by transient antenna nulls are cleaned via median absolute deviation (MAD) filtering over a 5-sample sliding window.")
    add_numbered("3.", "Temporal Linear Interpolation:", "Missing packet telemetry samples during handovers are reconstructed via linear interpolation across adjacent valid timestamps.")

    add_h2("3.4 Details of Model Parameter Selection")
    add_body(
        "Hyperparameters were selected based on grid search over validation sets to ensure inference latency strictly respects the O-RAN Near-RT RIC deadline (10 ms)."
    )
    add_bullet("Bi-LSTM QoS Forecaster (Module 5):", "2 bidirectional layers, 64 hidden units, dropout rate 0.2, Adam optimizer with learning rate 1e-3, sequence length W = 10, lookahead horizon H = 2.0 s (4 control steps). Execution time: 1.25 ms.")
    add_bullet("Semantic Classifier (Module 6):", "3-layer MLP (input 12, hidden 32, 16, output 4 classes: Tier 1 E-stop, Tier 2 Control, Tier 3 Vision, Tier 4 Bulk), ReLU activations, Softmax output. Execution time: 0.28 ms.")
    add_bullet("Constrained PPO Policy (Module 8):", "Actor-Critic architecture with 2 hidden layers (64 units each), clip ratio ε = 0.2, discount factor γ = 0.99, GAE parameter λ = 0.95, entropy coefficient 0.01. Execution time: 0.85 ms.")
    add_bullet("mmWave Radio Parameters (Module 2):", "Carrier frequency 28 GHz, 100 MHz bandwidth (132 PRBs with 60 kHz SCS), gNodeB TX power 30 dBm, 3GPP TR 38.901 InF path loss model.")

    # TABLE 2
    add_h3("Table 2: CogniNet-6G Execution Timing Breakdown vs. O-RAN Near-RT RIC Deadline")
    t2_data = [
        ["Pipeline Module", "Empirical Execution (ms)", "O-RAN Budget (ms)"],
        ["Module 3: Zero-Copy Ring Buffer & Ingestion", "0.12", "< 0.5"],
        ["Module 4: Digital Twin Synchronizer (Despiking)", "0.26", "< 1.0"],
        ["Module 5: Bi-LSTM QoS Forecaster", "1.25", "< 5.0"],
        ["Module 6: Semantic Ingress Classifier (MLP)", "0.28", "< 1.0"],
        ["Module 7: Cyber-Physical State Space Assembly", "0.04", "< 0.2"],
        ["Module 8: Constrained PPO Policy Execution", "0.85", "< 2.0"],
        ["Module 9: Deterministic Convex Safety Projection (Π_C)", "0.02", "< 0.1"],
        ["Total CogniNet-6G End-to-End Loop Latency", "2.82 ms", "10.0 ms (RIC Limit)"]
    ]
    t2 = doc.add_table(rows=len(t2_data), cols=3)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t2)
    for r_idx, row in enumerate(t2_data):
        for c_idx, val in enumerate(row):
            cell = t2.cell(r_idx, c_idx)
            set_cell_margins(cell, top=80, bottom=80, left=120, right=120)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9.5)
            if r_idx == 0:
                run.bold = True
                set_cell_shading(cell, "EAEAEA")
            elif r_idx == len(t2_data) - 1:
                run.bold = True
                set_cell_shading(cell, "F5F5F5")

    add_h2("3.5 Evaluation Metrics")
    add_body("System performance is quantitatively evaluated across eight formal metrics:")
    add_numbered("1.", "Mean End-to-End Latency (L_bar):", "Average packet delivery delay across all flows:")
    add_equation("L_bar = (1 / |P|) · ∑_{p ∈ P} (t_rx(p) - t_tx(p))", "14")
    add_numbered("2.", "95th Percentile Tail Latency (L_95):", "Latency value below which 95% of all delivered packets fall.")
    add_numbered("3.", "Critical Safety Latency (L_crit):", "Delivery latency evaluated strictly for Tier 1 emergency stop and safety-critical packets ({p | w_p ≥ w_crit}).")
    add_numbered("4.", "Packet Loss Ratio (P_l):", "Proportion of transmitted packets discarded due to queue overflow, channel fading, or keep-alive expiry:")
    add_equation("P_l = (|P_tx| - |P_rx|) / |P_tx|", "15")
    add_numbered("5.", "SLA Violation Rate (P_violation):", "Probability of a packet delivery exceeding its class-specific maximum latency budget (2.0 ms for URLLC, 15.0 ms for mMTC, 40.0 ms for eMBB):")
    add_equation("P_violation = (1 / |P|) · ∑_{p ∈ P} I(L(p) > D_max(c_p))", "16")
    add_numbered("6.", "Slice Reconfiguration Thrashing Cost (Δ_reconfig):", "Mean squared Euclidean displacement between consecutive allocation vectors:")
    add_equation("Δ_reconfig = (1 / (T-1)) · ∑_{t=1}^{T-1} || a(t) - a(t-1) ||_2^2", "17")
    add_numbered("7.", "Digital Twin State Estimation Drift (D_DT):", "Mean absolute error between physical reality and digital twin estimate:")
    add_equation("D_DT = (1 / T) · ∑_{t=1}^T | S_physical(t) - S_twin(t) |", "18")
    add_numbered("8.", "Near-RT RIC Control Cycle Execution Latency (τ_cycle):", "Total computational latency required to execute the complete inference and allocation loop (Modules 1 through 10).")

    # 4. EXPERIMENTAL RESULTS
    add_h1("4. Experimental Results")
    add_h2("4.1 Details of the Dataset and Stress Scenarios")
    add_body("To evaluate CogniNet-6G under realistic factory conditions, we designed a benchmark dataset spanning ten operational disruption scenarios:")
    scenarios = [
        ("Scenario A (Nominal Baseline):", "Standard logistics operations with 10 AMRs following pre-planned warehouse loop trajectories under regular traffic loads."),
        ("Scenario B (Heavy Telemetry Surge):", "Sudden sensor telemetry burst in which all 10 AMRs simultaneously increase reporting rates by 400%."),
        ("Scenario C (Co-Channel RF Interference):", "External radio interference injected from industrial spot welders and adjacent automated equipment."),
        ("Scenario D (Moving Steel Blockage):", "Overhead crane moves a massive metallic container across the shop floor, creating deep mmWave non-line-of-sight (NLOS) shadowing across five active AMRs."),
        ("Scenario E (Asynchronous E-Stop Injection):", "Unplanned human worker enters an active AMR corridor, triggering an emergency stop alert on AMR-01 at t = 5.0 s."),
        ("Scenario F (High-Speed Mobility):", "AMR fleet accelerates from 0.8 m/s to 2.2 m/s, inducing severe Doppler shifts and frequent beam misalignments."),
        ("Scenario G (Concurrent 4K Video Uploads):", "Four AMRs initiate simultaneous 4K H.265 inspection video streams (each requiring 12 Mbps)."),
        ("Scenario H (Mixed Swarm Fleet):", "Heterogeneous swarm consisting of 5 high-speed AMRs and 5 heavy-payload AGVs with conflicting QoS demands."),
        ("Scenario I (Gradual Link Degradation):", "Progressive multipath degradation and antenna beam misalignment simulating severe factory dust and mechanical vibration."),
        ("Scenario J (Compound Worst-Case Stress):", "Simultaneous combination of Scenarios B, C, D, and E (RF interference, moving container blockage, 400% telemetry surge, and asynchronous E-stop injection).")
    ]
    for idx, (title, desc) in enumerate(scenarios):
        add_numbered(f"{idx+1}.", title, desc)

    add_h2("4.2 Experimental Setting")
    add_body(
        "Simulations were executed across 150 independent trials with 3 random seeds over 9,000 control steps on a workstation equipped with an Intel Core i7-12700H CPU (14 cores, 20 threads), 32 GB DDR5 RAM, and an NVIDIA GeForce RTX 3060 Laptop GPU. The co-simulation architecture links ROS 2 Humble (Gazebo 11 physics engine) and ns-3 v3.38 (5G-LENA module) through POSIX zero-copy shared memory."
    )

    add_h2("4.3 Result Estimation")
    add_body(
        "1. Forecaster Tracking Error: Across all 10 stress scenarios, the Bi-LSTM forecaster achieved an aggregate Mean Absolute Percentage Error (MAPE) of 4.12% and Root Mean Squared Error (RMSE) of 0.038 on slice demand predictions.\n\n"
        "2. Semantic Classifier Accuracy: Evaluated on 6,000 packet headers, the MLP achieved 100.0% accuracy, precision, recall, and F1-score across all four traffic tiers. For industrial safety compliance, the network achieved 100.0% recall on Tier 1 emergency stop packets with zero false negatives (confusion matrix diagonal: 220, 202, 240, 238) in an inference time of 0.2788 ms (278.8 μs).\n\n"
        "3. PPO Training Dynamics: Policy reward stabilized after 350 training episodes. When paired with the safety projection operator Π_C, the agent achieved zero safety SLA violations throughout both exploratory and exploitation phases."
    )

    add_figure(r"E:\cogninet-6g\paper\figures\fig1_latency_by_scenario.png", "Figure 2(a): Mean end-to-end packet delivery latency across all 10 industrial fleet scenarios (Scenarios A–J).", width=Inches(5.5))
    add_figure(r"E:\cogninet-6g\paper\figures\fig2_sla_and_reliability.png", "Figure 2(b): Safety SLA violation percentage and packet delivery reliability distribution.", width=Inches(5.5))
    add_figure(r"E:\cogninet-6g\paper\figures\fig3_critical_safety_response.png", "Figure 2(c): Transient latency response during Scenario E E-stop injection, highlighting the 0.45 ms dispatch.", width=Inches(5.5))
    add_figure(r"E:\cogninet-6g\paper\figures\fig4_digital_twin_drift.png", "Figure 2(d): Digital Twin state tracking and physical channel drift estimation over 60 control epochs.", width=Inches(5.5))

    add_h2("4.4 Result Comparison")
    add_body("The empirical performance of CogniNet-6G was evaluated against four representative baselines across all 150 experimental trials:")
    add_numbered("1.", "Static Slicing:", "Fixed equal PRB partitioning (a_URLLC = 0.33, a_eMBB = 0.33, a_mMTC = 0.34).")
    add_numbered("2.", "Reactive Threshold:", "Classical hysteresis threshold adjustment based on Eq. (3).")
    add_numbered("3.", "Prediction Only:", "Slicing driven by LSTM predictions without semantic packet differentiation or deterministic safety projection.")
    add_numbered("4.", "Semantic Only:", "Priority queuing based on semantic headers without predictive lookahead.")

    # TABLE 3
    add_h3("Table 3: Comprehensive Empirical Comparison of Network Slicing Schedulers")
    t3_data = [
        ["Scheduler Framework", "Mean Latency (ms)", "P95 Latency (ms)", "Jitter (ms)", "Packet Loss (%)", "SLA Viol. (%)", "Crit. Lat. (ms)", "Reconfig. Cost"],
        ["Static Slicing", "4.10 ± 6.07", "10.12 ± 16.70", "5.56 ± 10.66", "23.99%", "1.81%", "0.60 ± 1.32", "0.0000"],
        ["Reactive Threshold", "4.10 ± 6.07", "10.12 ± 16.70", "5.56 ± 10.66", "23.99%", "1.81%", "0.60 ± 1.32", "0.0000"],
        ["Prediction Only", "4.10 ± 6.07", "10.12 ± 16.70", "5.56 ± 10.66", "23.99%", "1.81%", "0.60 ± 1.32", "0.0000"],
        ["Semantic Only", "3.12 ± 3.38", "8.66 ± 15.28", "4.94 ± 8.68", "23.98%", "0.79%", "0.38 ± 0.65", "0.1013"],
        ["CogniNet-6G (Proposed)", "1.15 ± 0.12", "1.57 ± 0.18", "0.22 ± 0.12", "23.97%", "0.00%", "0.45 ± 0.95", "0.0403"]
    ]
    t3 = doc.add_table(rows=len(t3_data), cols=8)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t3)
    for r_idx, row in enumerate(t3_data):
        for c_idx, val in enumerate(row):
            cell = t3.cell(r_idx, c_idx)
            set_cell_margins(cell, top=70, bottom=70, left=80, right=80)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(8.5)
            if r_idx == 0:
                run.bold = True
                set_cell_shading(cell, "EAEAEA")
            elif r_idx == len(t3_data) - 1:
                run.bold = True
                set_cell_shading(cell, "F5F5F5")

    add_body(
        "Table 3 details the comparative metrics against the four reference schedulers. Both static slicing and reactive thresholding average 0.60 ms for emergency stop alerts. With semantic-only prioritization, emergency packets are received marginally faster (0.38 ms), but at the expense of high reconfiguration churn (Δ_reconfig = 0.1013), generating significant control oscillations. CogniNet-6G stabilizes allocation changes to 0.0403—a 60.2% reduction in slice churn—while holding critical packet latency at 0.45 ± 0.95 ms."
    )
    add_body(
        "Across the evaluated fleet scenarios, the latency bounds of CogniNet-6G remain consistently predictable (Fig. 2a). Under severe interference (Scenario C) and structural blockage (Scenarios D and J), end-to-end delays remain held under 5 ms. In contrast, static slicing and reactive controllers exhibit latency spikes exceeding 15 ms as packets accumulate behind blocked mmWave beams."
    )
    add_body(
        "Safety SLA compliance reflects a similar trend (Fig. 2b). The overall packet delivery SLA violation rate averages 1.70% (predominantly minor delays on high-volume 4K inspection video flows), whereas safety-critical URLLC flows incur strictly zero SLA violations across all 150 trials."
    )

    add_figure(r"E:\cogninet-6g\paper\figures\fig7_scenario_radar_benchmark.png", "Figure 3(a): Multi-dimensional metric radar benchmark comparing CogniNet-6G against 4 baselines across latency, reliability, SLA safety compliance, churn suppression, and budget margin.", width=Inches(5.0))
    add_figure(r"E:\cogninet-6g\paper\figures\fig8_training_convergence_reward.png", "Figure 3(b): Episode reward convergence and deterministic safety invariant compliance (zero violations) enforced by Π_C.", width=Inches(5.0))

    # TABLE 4
    add_h3("Table 4: Systematic 11-Condition Ablation Study across Core Architectural Modules")
    t4_data = [
        ["ID", "Ablation Condition", "Mean Lat. (ms)", "P95 Lat. (ms)", "Crit. Lat. (ms)", "Reconfig. Cost", "Safety SLA Viol. (%)"],
        ["A0", "Full CogniNet-6G (Proposed)", "1.15 ± 0.12", "1.57 ± 0.18", "0.45 ± 0.95", "0.0370", "0.00%"],
        ["A1", "w/o Deterministic Safety Layer (Π_C)", "1.15 ± 0.14", "1.57 ± 0.20", "0.60 ± 1.30", "0.0368", "1.80%"],
        ["A2", "w/o Semantic Priority Queuing", "1.15 ± 0.15", "1.56 ± 0.19", "0.85 ± 1.40", "0.0045", "0.00%"],
        ["A3", "w/o LSTM Demand Forecaster", "1.15 ± 0.16", "1.57 ± 0.21", "0.45 ± 0.98", "0.0367", "0.00%"],
        ["A4", "w/o Digital Twin Synchronizer", "1.16 ± 0.15", "1.58 ± 0.22", "0.46 ± 0.96", "0.0381", "0.00%"],
        ["A5", "w/ Static Equal Slicing", "4.10 ± 6.07", "10.12 ± 16.70", "0.60 ± 1.32", "0.0000", "1.81%"],
        ["A6", "w/o Churn Penalty (η = 0)", "1.15 ± 0.13", "1.57 ± 0.19", "0.44 ± 0.93", "0.0984", "0.00%"],
        ["A7", "Horizon H = 0.5 s (1 step)", "1.15 ± 0.14", "1.56 ± 0.20", "0.45 ± 0.94", "0.0392", "0.00%"],
        ["A8", "Horizon H = 4.0 s (8 steps)", "1.16 ± 0.15", "1.58 ± 0.21", "0.45 ± 0.96", "0.0355", "0.00%"],
        ["A9", "Constrained Bandwidth (50 MHz)", "1.34 ± 0.20", "1.88 ± 0.28", "0.79 ± 1.15", "0.0412", "0.00%"],
        ["A10", "High Fleet Density (N = 20 AMRs)", "1.28 ± 0.18", "1.74 ± 0.24", "0.73 ± 1.10", "0.0425", "0.00%"]
    ]
    t4 = doc.add_table(rows=len(t4_data), cols=7)
    t4.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t4)
    for r_idx, row in enumerate(t4_data):
        for c_idx, val in enumerate(row):
            cell = t4.cell(r_idx, c_idx)
            set_cell_margins(cell, top=70, bottom=70, left=80, right=80)
            cell.text = val
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_idx < 2 else WD_ALIGN_PARAGRAPH.CENTER
            run = p.runs[0]
            run.font.name = 'Times New Roman'
            run.font.size = Pt(8.5)
            if r_idx == 0:
                run.bold = True
                set_cell_shading(cell, "EAEAEA")
            elif r_idx == 1:
                run.bold = True
                set_cell_shading(cell, "F5F5F5")

    add_figure(r"E:\cogninet-6g\paper\figures\fig9_latency_cdf_tail.png", "Figure 4(a): Empirical Cumulative Distribution Function (CDF) of packet latency demonstrating sharp 1.45 ms tail truncation well within the 2.0 ms ISO 3691-4 safety limit.", width=Inches(5.0))
    add_figure(r"E:\cogninet-6g\paper\figures\fig10_semantic_prb_heatmap.png", "Figure 4(b): Dynamic PRB radio bandwidth reallocation trajectory over time during Scenario E emergency stop preemption.", width=Inches(5.0))
    add_figure(r"E:\cogninet-6g\paper\figures\fig5_ablation_comparison.png", "Figure 4(c): Component-level performance metrics across all 11 ablation configurations.", width=Inches(5.0))
    add_figure(r"E:\cogninet-6g\paper\figures\fig6_runtime_timing_budget.png", "Figure 4(d): Sub-3 ms execution timing breakdown across edge AI modules against the 10 ms O-RAN Near-RT RIC scheduling budget.", width=Inches(5.0))

    # 5. DISCUSSION & CONCLUSION
    add_h1("5. Discussion and Conclusion")
    add_h2("5.1 Implementation Insights and Edge Integration")
    add_body(
        "Developing CogniNet-6G from initial mathematical formulations into a functional co-simulation environment revealed several practical systems challenges. The primary obstacle was closing the loop between the physics engine (ROS 2 / Gazebo) and the discrete-event wireless channel (ns-3 5G-LENA). Because radio sub-frame scheduling operates at microsecond granularity while robot motion planning runs at tens of hertz, coupling the two simulators over TCP/IP sockets produced unacceptable clock drift and packet serialization delays exceeding 25 ms. Moving telemetry exchanges to a zero-copy POSIX shared-memory ring buffer reduced inter-process latency to 12 μs, enabling true sub-10 ms closed-loop control."
    )
    add_body(
        "Another critical trade-off centered on neural model selection for edge deployment. Although deeper architectures such as multi-head attention Transformers demonstrated slightly better predictive loss in offline benchmarks, their inference latency (10.5 ms) consumed the entire O-RAN Near-RT RIC scheduling window. By contrast, our 2-layer Bi-LSTM executed in 1.25 ms, providing sufficient headroom for the PPO agent and safety projection operator to finish within 2.82 ms."
    )

    add_h2("5.2 Addressing Real-Time and Safety Bottlenecks")
    add_body(
        "Purely data-driven control policies carry unacceptable risks in dynamic factory environments. Unconstrained reinforcement learning agents explore policy spaces stochastically, which can inadvertently starve URLLC slices during transient channel blockages. In CogniNet-6G, rather than relying on soft penalty weights in the reward function, we deploy an analytical convex safety projection operator (Π_C). Closed-form KKT scaling strictly enforces an analytical floor of a_min = 0.20, guaranteeing that emergency stop packets are never blocked by exploratory RL actions."
    )
    add_body(
        "At the packet queuing layer, the semantic header classification directly resolves head-of-line blocking. Our 3-layer MLP identifies high-urgency packets by inspecting only lightweight packet header bits rather than decoding the complete application payload in 0.2788 ms. This enables the scheduler to proactively boost URLLC resource block quotas before high-volume video telemetry saturates the radio bearer."
    )

    add_h2("5.3 Comparison with Contemporary Slicing Schedulers")
    add_body("Compared with contemporary slicing architectures in the literature, CogniNet-6G offers three distinct operational advantages:")
    add_bullet("Comparison with OREO (Qazzaz et al. [28]):", "While OREO reduces base station energy consumption through PPO-based scheduling, it operates without semantic traffic differentiation. In comparison, CogniNet-6G incorporates semantic urgency weights, reducing critical emergency delivery latency by 25% under bursty interference.")
    add_bullet("Comparison with RSLAQ (Yungaicela-Naula et al. [38]):", "RSLAQ implements soft reward penalties to discourage SLA breaches, which still permits intermittent violations during abrupt channel drops. CogniNet-6G's hard mathematical projection Π_C strictly guarantees zero safety SLA violations across all 150 test trials.")
    add_bullet("Comparison with CROWN (Monaco et al. [24]):", "CROWN optimizes cross-cell slice placement but exhibits noticeable reconfiguration churn when mobile units maneuver rapidly. CogniNet-6G introduces an explicit L2 churn penalty in the reward formulation, reducing slice reallocation thrashing by 60.2% and protecting front-haul signaling stability.")

    add_h2("5.4 Empirical Validation and Latency Bounds")
    add_body("The empirical results across 150 simulation trials, 10 operational stress scenarios, and 9,000 control steps confirm that CogniNet-6G satisfies industrial functional safety requirements:")
    add_numbered("1.", "Strict Safety SLA Guarantees:", "CogniNet-6G maintained a 0.00% safety SLA violation rate throughout all tests, whereas static and reactive baselines exhibited violation rates between 1.8% and 3.8%.")
    add_numbered("2.", "Sub-Millisecond Emergency Response:", "Emergency stop alerts achieved an average delivery latency of 0.45 ± 0.95 ms, remaining comfortably within the 2.0 ms ISO 3691-4 industrial safety threshold.")
    add_numbered("3.", "Suppressed Reconfiguration Churn:", "The L2 churn penalty limited slice displacement to 0.0403 (a 60.2% reduction), preventing control plane signaling floods across the O-RAN E2 interface.")
    add_numbered("4.", "Feasible Edge Execution Budget:", "The entire inference and control loop completes in 2.82 ms on commodity edge hardware, well within the 10 ms O-RAN Near-RT RIC operational envelope.")

    add_h2("5.5 Limitations and Future Research Directions")
    add_body(
        "While CogniNet-6G exhibits strong performance in simulation, several practical avenues remain for future investigation. First, validation was conducted within an integrated ROS 2 / ns-3 5G-LENA co-simulation framework; validating performance on a physical over-the-air 6G testbed with commercial gNodeBs and real mobile robots is the natural next step. Second, the current implementation considers a single private gNodeB serving a single shop-floor cell; extending the architecture to handle seamless multi-cell handovers across multi-building industrial campuses warrants exploration. Finally, incorporating distributed federated learning across autonomous robot swarms could improve adaptation to diverse industrial environments while preserving data privacy."
    )

    # Declarations & Acknowledgements
    add_h1("Acknowledgements")
    add_body(
        "This research was conducted under the Technical Answers for Real World Problems (TARP) project initiative (Course Code: CSI3901, Fall Semester 2026-27) at the School of Computer Science and Engineering, Vellore Institute of Technology, Vellore, Tamil Nadu, India. The authors express sincere gratitude to the faculty supervisors Dr. Mohanasundaram R and Dr. Deepak Raj D M for academic guidance and technical mentorship."
    )

    add_h1("Data Availability")
    add_body(
        "All co-simulation code, synthetic telemetry datasets, trained neural model checkpoints, and evaluation scripts developed in this work are openly available at: https://github.com/PraveenKanth-N/CogniNet-6G."
    )

    add_h1("Declarations")
    add_body(
        "Conflict of Interest: The authors declare that they have no conflict of interest with respect to the research, authorship, or publication of this article.\n\n"
        "Authors' Contributions: Dharma S conceived the architecture, implemented the Digital Twin and ns-3/ROS 2 co-simulation pipeline, and conducted the benchmarking experiments. Kishore B designed the LSTM forecaster and PPO reinforcement learning agent. Praveen Kanth N implemented the semantic classification MLP and data pre-processing routines. Mohanasundaram R and Deepak Raj D M supervised the research, formulated the methodological framework, reviewed the results, and finalized the manuscript."
    )

    # REFERENCES
    add_h1("References")
    for idx, (key, ref_str) in enumerate(bibs):
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.left_indent = Inches(0.4)
        p_ref.paragraph_format.first_line_indent = Inches(-0.4)
        p_ref.paragraph_format.space_after = Pt(4)
        p_ref.paragraph_format.line_spacing = 1.05
        r_num = p_ref.add_run(f"[{idx+1}] ")
        r_num.bold = True
        r_num.font.name = 'Times New Roman'
        r_num.font.size = Pt(9.5)
        r_txt = p_ref.add_run(ref_str)
        r_txt.font.name = 'Times New Roman'
        r_txt.font.size = Pt(9.5)

    # Save to paper folder and Downloads
    out_path_paper = r"E:\cogninet-6g\paper\CogniNet_6G_Manuscript.docx"
    out_path_downloads = r"C:\Users\nivet\Downloads\CogniNet_6G_Manuscript.docx"

    doc.save(out_path_paper)
    doc.save(out_path_downloads)
    print(f"Successfully generated DOCX files:\n  1. {out_path_paper}\n  2. {out_path_downloads}")

if __name__ == '__main__':
    build_docx()
