"""
CogniNet-6G Closed-Loop Orchestration Engine (Algorithm 1 / Module 170)
Integrates Telemetry Acquisition, Digital Twin, Predictive Forecasting,
Semantic Intelligence, PPO Policy, Deterministic Safety Override, and
Action Actuation into a continuous closed-loop control cycle.
"""

import os
import sys
import time
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import torch

from sim.ros2_ws.factory_world import FactoryWorld
from sim.ros2_ws.fleet_simulator import FleetSimulator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import IndustrialTrafficGenerator, Scenario
from cogninet.telemetry.acquisition import TelemetryAcquisitionModule
from cogninet.digital_twin.sync_manager import DigitalTwinSyncManager
from cogninet.safety.safety_override import SafetyConstraintLayer
from cogninet.scheduler.reward import RewardCalculator
from cogninet.orchestration.action_handler import ActionHandler
from cogninet.prediction.lstm import LSTMTrafficPredictor
from cogninet.semantic.classifier import LightweightSemanticClassifier
from stable_baselines3 import PPO

class ClosedLoopOrchestrator:
    """
    Algorithm 1: AI-Native Closed-Loop Digital Twin Orchestrator for 6G Networks.
    Runs control cycle at interval dt = 0.5s.
    """
    def __init__(
        self,
        config: Dict[str, Any],
        scenario: Scenario = Scenario.A_NORMAL,
        model_paths: Optional[Dict[str, str]] = None,
        enable_safety_override: bool = True,
        enable_prediction: bool = True,
        enable_semantic: bool = True,
        policy_type: str = "ppo",  # "ppo", "static", "reactive"
        random_seed: int = 42
    ):
        self.config = config
        self.scenario = scenario
        self.enable_safety_override = enable_safety_override
        self.enable_prediction = enable_prediction
        self.enable_semantic = enable_semantic
        self.policy_type = policy_type.lower()
        self.random_seed = random_seed

        self.num_robots = config.get("fleet", {}).get("num_robots", 10)
        self.robot_ids = config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(self.num_robots)])
        self.r_max_mbps = config.get("network", {}).get("r_max_mbps", 100.0)
        self.dt = config.get("timing", {}).get("delta_t", 0.5)

        # Reward calculator
        rw = config.get("reward_weights", {})
        self.reward_calc = RewardCalculator(
            alpha=rw.get("alpha", 0.35),
            beta=rw.get("beta", 0.25),
            eta=rw.get("eta", 0.20),
            zeta=rw.get("zeta", 0.10),
            lambda_reconfig=rw.get("lambda_reconfig", 0.10)
        )

        # Safety override layer
        self.safety_layer = SafetyConstraintLayer(
            r_max_mbps=self.r_max_mbps,
            w_crit=config.get("safety", {}).get("w_crit", 0.85),
            d_max_ms=config.get("safety", {}).get("d_max_ms", 10.0),
            min_critical_bandwidth_mbps=15.0
        )

        # Action handler
        self.action_handler = ActionHandler(r_max_mbps=self.r_max_mbps)

        # Device
        self.device = torch.device("cpu")

        # Load models
        model_paths = model_paths or {}
        self.predictor = LSTMTrafficPredictor(input_dim=4, hidden_dim=64, num_layers=2, output_dim=4).to(self.device)
        pred_p = model_paths.get("predictor")
        if pred_p and os.path.exists(pred_p):
            self.predictor.load_state_dict(torch.load(pred_p, map_location=self.device))
        self.predictor.eval()

        self.semantic_model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4).to(self.device)
        sem_p = model_paths.get("semantic")
        if sem_p and os.path.exists(sem_p):
            self.semantic_model.load_state_dict(torch.load(sem_p, map_location=self.device))
        self.semantic_model.eval()

        self.rl_policy: Optional[PPO] = None
        rl_p = model_paths.get("ppo")
        if self.policy_type == "ppo" and rl_p and os.path.exists(rl_p):
            self.rl_policy = PPO.load(rl_p, device=self.device)

        # Warm up neural inference pipelines to eliminate cold-start latency spikes
        with torch.no_grad():
            dummy_hist = torch.zeros((1, 10, 4), dtype=torch.float32, device=self.device)
            _ = self.predictor(dummy_hist)
            dummy_sem = {"task_type": "TELEMETRY", "urgency": 0.2, "is_critical": False, "flow_type": "mMTC", "payload_bytes": 512}
            _ = self.semantic_model.predict_metadata(dummy_sem, device=self.device)
            if self.rl_policy is not None:
                dummy_obs = np.zeros(29, dtype=np.float32)
                _ = self.rl_policy.predict(dummy_obs, deterministic=True)

        # Co-simulation instances
        self._init_simulation()

    def _init_simulation(self):
        """Initializes simulated physical plant and telemetry infrastructure."""
        self.world = FactoryWorld()
        self.fleet = FleetSimulator(self.config, self.world, random_seed=self.random_seed)
        self.net = Ns3NetworkModel(self.config, random_seed=self.random_seed)
        self.traffic_gen = IndustrialTrafficGenerator(self.config, seed=self.random_seed)
        self.acq = TelemetryAcquisitionModule(expected_robot_ids=self.robot_ids)
        self.dt_mgr = DigitalTwinSyncManager(self.config, history_k=10)

        self.current_allocations = {rid: self.r_max_mbps / self.num_robots for rid in self.robot_ids}
        self.net.reallocate(self.current_allocations)

        self.current_time = 0.0
        self.step_idx = 0
        self.execution_log: List[Dict[str, Any]] = []

    def _get_feature_vector(self, state_4d: List[float]) -> np.ndarray:
        """Runs LSTM predictor over rolling history window from Digital Twin."""
        if not self.enable_prediction:
            return np.array(state_4d, dtype=np.float32)

        hist_window = self.dt_mgr.get_history_window()  # (10, 4)
        with torch.no_grad():
            hist_t = torch.from_numpy(hist_window).unsqueeze(0).to(self.device)
            pred_t = self.predictor(hist_t).squeeze(0).cpu().numpy()
        return pred_t

    def _compute_semantic_weights(self, packets: List[Dict[str, Any]]) -> Dict[str, float]:
        """Runs semantic classifier for incoming traffic packets."""
        weights_map = {rid: 0.15 for rid in self.robot_ids}
        if not self.enable_semantic:
            return {rid: 0.5 for rid in self.robot_ids}

        for p in packets:
            rid = p.get("robot_id")
            if rid in weights_map:
                w_pkt = self.semantic_model.predict_metadata(p, device=self.device)
                weights_map[rid] = max(weights_map[rid], float(w_pkt))
        return weights_map

    def _decide_allocation(
        self,
        state_vec: List[float],
        pred_state: np.ndarray,
        weights: Dict[str, float],
        max_duration: float
    ) -> Tuple[Dict[str, float], float]:
        """
        Policy decision step:
        Computes allocation vector via PPO, Static, or Reactive Threshold.
        """
        start_t = time.perf_counter()

        if self.policy_type == "static":
            alloc = {rid: self.r_max_mbps / self.num_robots for rid in self.robot_ids}

        elif self.policy_type == "reactive":
            raw_scores = {}
            for rid in self.robot_ids:
                raw_scores[rid] = max(0.1, state_vec[0] * weights.get(rid, 0.5))
            sum_s = sum(raw_scores.values())
            alloc = {rid: (raw_scores[rid] / sum_s) * self.r_max_mbps for rid in self.robot_ids}

        else:
            # PPO Policy
            # State vector S(t): 4 normalized
            s_norm = [
                min(2.0, state_vec[0] / 50.0),
                min(2.0, state_vec[1] / 10.0),
                min(1.0, state_vec[2]),
                min(1.0, state_vec[3])
            ]
            # Predicted state S_hat(t+Delta): 4 normalized
            s_hat_norm = [
                min(2.0, max(0.0, float(pred_state[0]) / 50.0)),
                min(2.0, max(0.0, float(pred_state[1]) / 10.0)),
                min(1.0, max(0.0, float(pred_state[2]))),
                min(1.0, max(0.0, float(pred_state[3])))
            ]
            weights_vec = [weights.get(rid, 0.15) for rid in self.robot_ids]
            a_prev_norm = [self.current_allocations.get(rid, 10.0) / self.r_max_mbps for rid in self.robot_ids]
            t_norm = [min(1.0, self.current_time / max(1.0, max_duration))]

            obs = np.array(s_norm + s_hat_norm + weights_vec + a_prev_norm + t_norm, dtype=np.float32)

            if self.rl_policy is not None:
                action_logits, _ = self.rl_policy.predict(obs, deterministic=True)
            else:
                action_logits = np.array([weights.get(rid, 0.5) for rid in self.robot_ids], dtype=np.float32)

            exp_a = np.exp(action_logits - np.max(action_logits))
            probs = exp_a / np.sum(exp_a)
            alloc = {rid: float(probs[i] * self.r_max_mbps) for i, rid in enumerate(self.robot_ids)}

        decision_ms = (time.perf_counter() - start_t) * 1000.0
        return alloc, decision_ms

    def step(self, max_duration: float = 60.0) -> Dict[str, Any]:
        """
        Executes one discrete closed-loop control cycle (Algorithm 1).
        """
        loop_start = time.perf_counter()
        t = self.current_time

        # 1. Step fleet simulation & generate traffic
        e_stop = "r01" if (self.scenario == Scenario.E_CRITICAL_SAFETY and self.step_idx in [20, 21]) else None
        fleet_tel = self.fleet.step(emergency_stop_robot=e_stop)
        packets = self.traffic_gen.generate_interval_traffic(
            self.step_idx, t, self.scenario, fleet_tel, self.num_robots
        )
        positions = {rid: (r["x"], r["y"]) for rid, r in fleet_tel.items()}

        # 2. Transmit interval under current slice allocation
        state_vec, flow_res = self.net.transmit_interval(packets, positions)

        # 3. Telemetry Acquisition & Packaging (Module 100)
        rec = self.acq.clean_and_package(fleet_tel, state_vec, flow_res, packets, timestamp=t)

        # 4. Digital Twin Synchronization (Module 110)
        sync_res = self.dt_mgr.update_from_telemetry(rec)

        # 5. Predictive Traffic Forecasting (Module 120)
        t_pred_start = time.perf_counter()
        pred_state = self._get_feature_vector(state_vec)
        pred_ms = (time.perf_counter() - t_pred_start) * 1000.0

        # 6. Semantic Prioritization (Module 130)
        t_sem_start = time.perf_counter()
        weights = self._compute_semantic_weights(packets)
        sem_ms = (time.perf_counter() - t_sem_start) * 1000.0

        # 7. Policy Slicing Decision (Module 140)
        raw_alloc, decision_ms = self._decide_allocation(state_vec, pred_state, weights, max_duration)

        # 8. Deterministic Safety Screening (Module 160)
        t_safe_start = time.perf_counter()
        if self.enable_safety_override:
            safe_alloc, override_applied = self.safety_layer.enforce(raw_alloc, weights, step=self.step_idx)
        else:
            safe_alloc = raw_alloc.copy()
            override_applied = False
        safe_ms = (time.perf_counter() - t_safe_start) * 1000.0

        # 9. Action Dispatch & Actuation (Module 150)
        t_act_start = time.perf_counter()
        dispatch_meta = self.action_handler.dispatch(
            net_model=self.net,
            allocation_vector=safe_alloc,
            timestamp=t,
            previous_alloc=self.current_allocations
        )
        act_ms = (time.perf_counter() - t_act_start) * 1000.0
        self.current_allocations = safe_alloc.copy()

        # 10. Performance Metrics & Reward Feedback (Module 170)
        reconfig_cost = dispatch_meta["reconfiguration_cost"]
        sla_lat = self.config.get("network", {}).get("sla_latency_threshold_ms", 45.0)
        sla_loss = self.config.get("network", {}).get("sla_packet_loss_max", 0.05)
        sla_ok = (rec.system_state[0] <= sla_lat) and (rec.system_state[2] <= sla_loss)

        reward_breakdown = self.reward_calc.compute(
            system_state=rec.system_state,
            sla_satisfied=sla_ok,
            current_action=safe_alloc,
            previous_action=self.current_allocations,
            r_max=self.r_max_mbps
        )
        reward = reward_breakdown.total_reward
        self.dt_mgr.record_orchestration_action(safe_alloc)
        self.dt_mgr.record_feedback(reward, rec.system_state)

        total_loop_ms = (time.perf_counter() - loop_start) * 1000.0

        sla_thresh = self.config.get("network", {}).get("sla_latency_threshold_ms", 45.0)
        sla_violations = sum(1 for fl in flow_res.values() if fl.mean_latency_ms > sla_thresh)

        step_record = {
            "step": self.step_idx,
            "timestamp": round(t, 2),
            "state": [round(float(x), 4) for x in state_vec],
            "predicted_state": [round(float(x), 4) for x in pred_state],
            "reward": round(float(reward), 4),
            "sla_violations": sla_violations,
            "safety_override_applied": override_applied,
            "reconfig_cost": round(reconfig_cost, 6),
            "weights": {k: round(v, 4) for k, v in weights.items()},
            "allocations": {k: round(v, 3) for k, v in safe_alloc.items()},
            "twin_drift": round(float(sync_res.get("drift", 0.0)), 4),
            "timing_ms": {
                "prediction_ms": round(pred_ms, 4),
                "semantic_ms": round(sem_ms, 4),
                "decision_ms": round(decision_ms, 4),
                "safety_ms": round(safe_ms, 4),
                "actuator_ms": round(act_ms, 4),
                "total_loop_ms": round(total_loop_ms, 4)
            }
        }
        self.execution_log.append(step_record)

        self.current_time += self.dt
        self.step_idx += 1
        return step_record

    def run_simulation(self, duration_s: float = 30.0) -> List[Dict[str, Any]]:
        """Runs the closed-loop orchestrator for duration_s seconds."""
        num_steps = int(duration_s / self.dt)
        for _ in range(num_steps):
            self.step(max_duration=duration_s)
        return self.execution_log
