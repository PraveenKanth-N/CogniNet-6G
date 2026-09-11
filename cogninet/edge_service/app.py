"""
CogniNet-6G Edge Orchestration Microservice
FastAPI Application serving real-time predictions, semantic classifications,
PPO policy allocations, and closed-loop control decisions at the edge.
"""

import os
import sys
import time
import yaml
from typing import Dict, List, Any, Optional
import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from cogninet.prediction.lstm import LSTMTrafficPredictor
from cogninet.semantic.classifier import LightweightSemanticClassifier
from cogninet.safety.safety_override import SafetyConstraintLayer
from cogninet.feedback.loop import ClosedLoopOrchestrator
from experiments.scenarios.traffic_generator import Scenario
from stable_baselines3 import PPO

app = FastAPI(
    title="CogniNet-6G Edge Orchestration Service",
    version="1.0.0",
    description="Edge microservice exposing sub-millisecond AI inference and 6G slicing APIs"
)

# Global State Container
class ServiceContainer:
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.predictor: Optional[LSTMTrafficPredictor] = None
        self.semantic_classifier: Optional[LightweightSemanticClassifier] = None
        self.ppo_policy: Optional[PPO] = None
        self.safety_layer: Optional[SafetyConstraintLayer] = None
        self.orchestrator: Optional[ClosedLoopOrchestrator] = None
        self.start_time: float = time.time()
        self.device = torch.device("cpu")

container = ServiceContainer()

def load_services():
    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    if os.path.exists(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as f:
            container.config = yaml.safe_load(f)
    else:
        container.config = {"network": {"r_max_mbps": 100.0}, "fleet": {"num_robots": 10}}

    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    pred_path = os.path.join(models_dir, "lstm_predictor.pt")
    sem_path = os.path.join(models_dir, "semantic_classifier.pt")
    ppo_path = os.path.join(models_dir, "ppo_scheduler.zip")

    # Predictor
    container.predictor = LSTMTrafficPredictor(input_dim=4, hidden_dim=64, num_layers=2, output_dim=4).to(container.device)
    if os.path.exists(pred_path):
        container.predictor.load_state_dict(torch.load(pred_path, map_location=container.device))
    container.predictor.eval()

    # Semantic Classifier
    container.semantic_classifier = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4).to(container.device)
    if os.path.exists(sem_path):
        container.semantic_classifier.load_state_dict(torch.load(sem_path, map_location=container.device))
    container.semantic_classifier.eval()

    # PPO Policy
    if os.path.exists(ppo_path):
        container.ppo_policy = PPO.load(ppo_path, device=container.device)

    # Safety Layer
    r_max = container.config.get("network", {}).get("r_max_mbps", 100.0)
    container.safety_layer = SafetyConstraintLayer(
        r_max_mbps=r_max,
        w_crit=container.config.get("safety", {}).get("w_crit", 0.85),
        d_max_ms=container.config.get("safety", {}).get("d_max_ms", 10.0),
        min_critical_bandwidth_mbps=15.0
    )

    # Orchestrator
    model_paths = {
        "predictor": pred_path,
        "semantic": sem_path,
        "ppo": ppo_path
    }
    container.orchestrator = ClosedLoopOrchestrator(
        config=container.config,
        scenario=Scenario.A_NORMAL,
        model_paths=model_paths,
        enable_safety_override=True,
        policy_type="ppo",
        random_seed=42
    )

# Eagerly load models and orchestrator upon module import
load_services()

@app.on_event("startup")
def startup_event():
    load_services()

# --- Request / Response Models ---

class PredictRequest(BaseModel):
    history: List[List[float]] = Field(..., description="Rolling history window of shape (k, 4)")

class PredictResponse(BaseModel):
    predicted_state: List[float]
    inference_time_ms: float

class PacketItem(BaseModel):
    robot_id: str
    task_type: str = "TELEMETRY"
    urgency: float = 0.2
    is_critical: bool = False
    flow_type: str = "mMTC"
    payload_bytes: int = 512

class ClassifyRequest(BaseModel):
    packets: List[PacketItem]

class ClassifyResponse(BaseModel):
    weights: Dict[str, float]
    inference_time_ms: float

class AllocateRequest(BaseModel):
    state_vec: List[float]
    predicted_state: List[float]
    weights: Dict[str, float]
    current_allocations: Optional[Dict[str, float]] = None

class AllocateResponse(BaseModel):
    allocations: Dict[str, float]
    safety_override_applied: bool
    inference_time_ms: float

# --- Endpoints ---

@app.get("/health")
def get_health():
    uptime_s = time.time() - container.start_time
    return {
        "status": "healthy",
        "service": "cogninet-6g-edge",
        "uptime_seconds": round(uptime_s, 2),
        "models_loaded": {
            "traffic_predictor": container.predictor is not None,
            "semantic_classifier": container.semantic_classifier is not None,
            "ppo_scheduler": container.ppo_policy is not None,
            "safety_layer": container.safety_layer is not None
        }
    }

@app.get("/state")
def get_state():
    if not container.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {
        "current_time": container.orchestrator.current_time,
        "step_idx": container.orchestrator.step_idx,
        "current_allocations": container.orchestrator.current_allocations,
        "history_buffer_length": len(container.orchestrator.dt_mgr.history_buffer)
    }

@app.post("/predict", response_model=PredictResponse)
def predict_traffic(req: PredictRequest):
    if not container.predictor:
        raise HTTPException(status_code=503, detail="Predictor model not available")

    hist = np.array(req.history, dtype=np.float32)
    if hist.ndim != 2 or hist.shape[1] != 4:
        raise HTTPException(status_code=400, detail=f"Expected history shape (k, 4), got {hist.shape}")

    start_t = time.perf_counter()
    x_t = torch.from_numpy(hist).unsqueeze(0).to(container.device)
    with torch.no_grad():
        pred = container.predictor(x_t).squeeze(0).cpu().numpy()
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    return PredictResponse(
        predicted_state=[round(float(v), 4) for v in pred],
        inference_time_ms=round(elapsed_ms, 4)
    )

@app.post("/classify", response_model=ClassifyResponse)
def classify_packets(req: ClassifyRequest):
    if not container.semantic_classifier:
        raise HTTPException(status_code=503, detail="Semantic classifier not available")

    start_t = time.perf_counter()
    weights: Dict[str, float] = {}
    for p in req.packets:
        w = container.semantic_classifier.predict_metadata(p.model_dump(), device=container.device)
        prev_w = weights.get(p.robot_id, 0.0)
        weights[p.robot_id] = max(prev_w, float(w))
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    return ClassifyResponse(
        weights={k: round(v, 4) for k, v in weights.items()},
        inference_time_ms=round(elapsed_ms, 4)
    )

@app.post("/allocate", response_model=AllocateResponse)
def allocate_slices(req: AllocateRequest):
    start_t = time.perf_counter()
    r_max = container.config.get("network", {}).get("r_max_mbps", 100.0)
    num_robots = container.config.get("fleet", {}).get("num_robots", 10)
    robot_ids = container.config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(num_robots)])

    prev_alloc = req.current_allocations or {rid: r_max / num_robots for rid in robot_ids}

    # Normalize observation for PPO
    s_norm = [min(2.0, req.state_vec[0] / 50.0), min(2.0, req.state_vec[1] / 10.0), min(1.0, req.state_vec[2]), min(1.0, req.state_vec[3])]
    s_hat_norm = [min(2.0, max(0.0, req.predicted_state[0]) / 50.0), min(2.0, max(0.0, req.predicted_state[1]) / 10.0), min(1.0, max(0.0, req.predicted_state[2])), min(1.0, max(0.0, req.predicted_state[3]))]
    w_vec = [req.weights.get(rid, 0.15) for rid in robot_ids]
    a_prev_norm = [prev_alloc.get(rid, 10.0) / r_max for rid in robot_ids]
    t_norm = [0.5]

    obs = np.array(s_norm + s_hat_norm + w_vec + a_prev_norm + t_norm, dtype=np.float32)

    if container.ppo_policy:
        action_logits, _ = container.ppo_policy.predict(obs, deterministic=True)
    else:
        action_logits = np.array([req.weights.get(rid, 0.5) for rid in robot_ids], dtype=np.float32)

    exp_a = np.exp(action_logits - np.max(action_logits))
    probs = exp_a / np.sum(exp_a)
    raw_alloc = {rid: float(probs[i] * r_max) for i, rid in enumerate(robot_ids)}

    # Apply Safety Override
    safe_alloc, override_applied = container.safety_layer.enforce(raw_alloc, req.weights)
    elapsed_ms = (time.perf_counter() - start_t) * 1000.0

    return AllocateResponse(
        allocations={k: round(v, 3) for k, v in safe_alloc.items()},
        safety_override_applied=override_applied,
        inference_time_ms=round(elapsed_ms, 4)
    )

@app.post("/decision")
def step_decision():
    if not container.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    step_record = container.orchestrator.step()
    return step_record
