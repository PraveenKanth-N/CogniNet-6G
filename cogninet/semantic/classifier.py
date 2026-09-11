"""
Module 130: Lightweight Semantic Priority Classifier
PyTorch MLP architecture for low-latency inline message metadata classification.
Maps message metadata vector m_i(t) in R^8 to continuous priority weight w_i(t) in [0, 1].
"""

import torch
import torch.nn as nn
from typing import Dict, List, Any, Tuple
from cogninet.semantic.taxonomy import SemanticClass, SEMANTIC_BASE_WEIGHTS

class LightweightSemanticClassifier(nn.Module):
    """
    Lightweight 3-layer MLP designed for sub-millisecond per-packet inference.
    Input Features (8):
      1. task_type_idx (normalized 0..1)
      2. urgency (0..1)
      3. is_safety_critical (0 or 1)
      4. payload_size_norm (normalized by 64KB)
      5. current_speed (m/s, normalized)
      6. distance_to_obstacle_norm (normalized)
      7. battery_pct_norm (0..1)
      8. zone_idx (normalized)
    """
    def __init__(self, input_dim: int = 8, hidden_dim: int = 32, num_classes: int = 4):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes

        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, num_classes)
        )

        # Class weight scalar vector [0.95, 0.75, 0.50, 0.15]
        self.register_buffer(
            "class_weights",
            torch.tensor([0.95, 0.75, 0.50, 0.15], dtype=torch.float32)
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: Tensor of shape (batch_size, 8)
        Returns:
            logits: Tensor of shape (batch_size, 4)
            continuous_weights: Tensor of shape (batch_size,) representing w_i(t)
        """
        logits = self.net(x)
        probs = torch.softmax(logits, dim=-1)
        # Expected continuous importance score w_i(t)
        continuous_weights = torch.sum(probs * self.class_weights, dim=-1)
        return logits, continuous_weights

    def predict_metadata(self, metadata: Dict[str, Any], device: torch.device = None) -> float:
        """Inline inference helper for single message metadata dictionary."""
        dev = device if device is not None else next(self.parameters()).device
        # Vectorize metadata
        task_map = {"EMERGENCY_STOP": 0.0, "NAVIGATION": 0.25, "MISSION_SYNC": 0.5, "INSPECTION_VIDEO": 0.75, "TELEMETRY": 1.0}
        t_idx = task_map.get(metadata.get("task_type", "TELEMETRY"), 1.0)
        urgency = float(metadata.get("urgency", 0.1))
        is_crit = 1.0 if metadata.get("is_critical", False) else 0.0
        payload_norm = min(1.0, float(metadata.get("payload_bytes", 128)) / 65536.0)
        speed = min(1.0, float(metadata.get("speed", 0.5)) / 2.0)
        dist_obs = min(1.0, float(metadata.get("obstacle_dist", 10.0)) / 20.0)
        batt = float(metadata.get("battery_pct", 100.0)) / 100.0
        zone_norm = 0.5

        feat = torch.tensor([[t_idx, urgency, is_crit, payload_norm, speed, dist_obs, batt, zone_norm]], dtype=torch.float32, device=dev)
        self.eval()
        with torch.no_grad():
            _, w = self.forward(feat)
            return float(w.item())
