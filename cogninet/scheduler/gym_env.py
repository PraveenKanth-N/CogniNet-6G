"""
Gymnasium Reinforcement Learning Environment for 6G Network Slicing
Wraps co-simulation, telemetry, digital twin, traffic prediction, and semantic classification.
Action space: Box(N, [-1, 1]) mapped to simplex sum(R_i) = R_max.
Observation space: [S(t), S_hat(t+Delta), {w_i(t)}, a(t-1), t_norm] in R^29.
"""

import os
import sys
import numpy as np
import torch
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, List, Any, Tuple, Optional

from sim.ros2_ws.factory_world import FactoryWorld
from sim.ros2_ws.fleet_simulator import FleetSimulator
from sim.ns3.ns3_network_model import Ns3NetworkModel
from experiments.scenarios.traffic_generator import IndustrialTrafficGenerator, Scenario
from cogninet.telemetry.acquisition import TelemetryAcquisitionModule
from cogninet.digital_twin.sync_manager import DigitalTwinSyncManager
from cogninet.safety.safety_override import SafetyConstraintLayer
from cogninet.scheduler.reward import RewardCalculator
from cogninet.prediction.lstm import LSTMTrafficPredictor
from cogninet.semantic.classifier import LightweightSemanticClassifier

class CogniNetSlicingEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        config: Dict[str, Any],
        scenario: Scenario = Scenario.B_CONGESTION_BURST,
        max_steps: int = 60,
        enable_safety_override: bool = True,
        predictor_weights_path: Optional[str] = None,
        semantic_weights_path: Optional[str] = None,
        random_seed: int = 42
    ):
        super().__init__()
        self.config = config
        self.scenario = scenario
        self.max_steps = max_steps
        self.enable_safety_override = enable_safety_override
        self.seed = random_seed

        self.num_robots = config.get("fleet", {}).get("num_robots", 10)
        self.robot_ids = config.get("fleet", {}).get("robot_ids", [f"r{i+1:02d}" for i in range(self.num_robots)])
        self.r_max_mbps = config.get("network", {}).get("r_max_mbps", 100.0)
        self.dt = config.get("timing", {}).get("delta_t", 0.5)

        # 29-dimensional observation space:
        # S(t): 4, S_hat(t+Delta): 4, {w_i(t)}: 10, a(t-1)/R_max: 10, t/T_max: 1
        obs_dim = 4 + 4 + self.num_robots + self.num_robots + 1
        self.observation_space = spaces.Box(
            low=0.0, high=10.0, shape=(obs_dim,), dtype=np.float32
        )

        # Action space: continuous logits for N robots in [-1.0, 1.0]
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(self.num_robots,), dtype=np.float32
        )

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

        # Load models if paths provided
        self.device = torch.device("cpu")
        self.predictor = LSTMTrafficPredictor(input_dim=4, hidden_dim=64, num_layers=2, output_dim=4).to(self.device)
        if predictor_weights_path and os.path.exists(predictor_weights_path):
            self.predictor.load_state_dict(torch.load(predictor_weights_path, map_location=self.device))
        self.predictor.eval()

        self.semantic_model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4).to(self.device)
        if semantic_weights_path and os.path.exists(semantic_weights_path):
            self.semantic_model.load_state_dict(torch.load(semantic_weights_path, map_location=self.device))
        self.semantic_model.eval()

        # Co-simulation objects
        self.world = None
        self.fleet = None
        self.net = None
        self.traffic_gen = None
        self.acq = None
        self.dt_mgr = None

        self.current_step = 0
        self.prev_action = {rid: self.r_max_mbps / self.num_robots for rid in self.robot_ids}

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        if seed is not None:
            self.seed = seed

        self.current_step = 0
        self.prev_action = {rid: self.r_max_mbps / self.num_robots for rid in self.robot_ids}

        self.world = FactoryWorld()
        self.fleet = FleetSimulator(self.config, self.world, random_seed=self.seed)
        self.net = Ns3NetworkModel(self.config, random_seed=self.seed)
        self.traffic_gen = IndustrialTrafficGenerator(self.config, seed=self.seed)
        self.acq = TelemetryAcquisitionModule(expected_robot_ids=self.robot_ids)
        self.dt_mgr = DigitalTwinSyncManager(self.config, history_k=10)

        # Step initial snapshot
        fleet_tel = self.fleet.step()
        packets = self.traffic_gen.generate_interval_traffic(0, 0.0, self.scenario, fleet_tel, self.num_robots)
        positions = {rid: (r["x"], r["y"]) for rid, r in fleet_tel.items()}
        state_vec, flow_res = self.net.transmit_interval(packets, positions)
        rec = self.acq.clean_and_package(fleet_tel, state_vec, flow_res, packets, timestamp=0.0)
        self.dt_mgr.update_from_telemetry(rec)

        obs = self._build_observation(state_vec, packets)
        return obs, {}

    def _build_observation(self, state_vec: List[float], packets: List[Dict[str, Any]]) -> np.ndarray:
        # 1. State vector S(t): 4 normalized
        s_norm = [
            min(2.0, state_vec[0] / 50.0),
            min(2.0, state_vec[1] / 10.0),
            min(1.0, state_vec[2]),
            min(1.0, state_vec[3])
        ]

        # 2. Predicted state S_hat(t+Delta): 4
        hist_window = self.dt_mgr.get_history_window()  # (10, 4)
        with torch.no_grad():
            hist_t = torch.from_numpy(hist_window).unsqueeze(0).to(self.device)  # (1, 10, 4)
            pred_t = self.predictor(hist_t).squeeze(0).cpu().numpy()
        s_hat_norm = [
            min(2.0, max(0.0, float(pred_t[0]) / 50.0)),
            min(2.0, max(0.0, float(pred_t[1]) / 10.0)),
            min(1.0, max(0.0, float(pred_t[2]))),
            min(1.0, max(0.0, float(pred_t[3])))
        ]

        # 3. Semantic weights w_i(t): 10
        weights_map = {rid: 0.15 for rid in self.robot_ids}
        for p in packets:
            rid = p.get("robot_id")
            if rid in weights_map:
                w_pkt = self.semantic_model.predict_metadata(p, device=self.device)
                weights_map[rid] = max(weights_map[rid], w_pkt)
        weights_vec = [weights_map[rid] for rid in self.robot_ids]

        # 4. Previous action normalized: 10
        a_prev_norm = [self.prev_action.get(rid, 10.0) / self.r_max_mbps for rid in self.robot_ids]

        # 5. Step normalized: 1
        t_norm = [self.current_step / float(self.max_steps)]

        obs = np.array(s_norm + s_hat_norm + weights_vec + a_prev_norm + t_norm, dtype=np.float32)
        return obs

    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1
        sim_time = self.current_step * self.dt

        # Map raw action Box(N, [-1, 1]) via softmax to simplex sum(R_i) = R_max
        exp_a = np.exp(action - np.max(action))
        softmax_shares = exp_a / np.sum(exp_a)
        cand_alloc = {rid: float(softmax_shares[i] * self.r_max_mbps) for i, rid in enumerate(self.robot_ids)}

        # Determine active packets & semantic weights
        e_stop = "r01" if (self.scenario == Scenario.E_CRITICAL_SAFETY and self.current_step in [20, 21]) else None
        fleet_tel = self.fleet.step(emergency_stop_robot=e_stop)
        packets = self.traffic_gen.generate_interval_traffic(
            self.current_step, sim_time, self.scenario, fleet_tel, self.num_robots
        )

        semantic_weights = {rid: 0.15 for rid in self.robot_ids}
        for p in packets:
            rid = p.get("robot_id")
            if rid in semantic_weights:
                w = self.semantic_model.predict_metadata(p, device=self.device)
                semantic_weights[rid] = max(semantic_weights[rid], w)

        # Deterministic Safety Override Layer
        override_applied = False
        if self.enable_safety_override:
            safe_alloc, override_applied = self.safety_layer.enforce(cand_alloc, semantic_weights, step=self.current_step)
        else:
            safe_alloc = cand_alloc.copy()

        # Actuate network
        self.net.reallocate(safe_alloc)
        positions = {rid: (r["x"], r["y"]) for rid, r in fleet_tel.items()}
        state_vec, flow_res = self.net.transmit_interval(packets, positions)

        # Telemetry & Twin update
        rec = self.acq.clean_and_package(fleet_tel, state_vec, flow_res, packets, timestamp=sim_time)
        self.dt_mgr.update_from_telemetry(rec)
        self.dt_mgr.record_orchestration_action(safe_alloc)

        # Reward computation
        sla_ok = (rec.system_state[0] <= self.config["network"]["sla_latency_threshold_ms"]) and \
                 (rec.system_state[2] <= self.config["network"]["sla_packet_loss_max"])
        reward_breakdown = self.reward_calc.compute(
            rec.system_state, sla_ok, safe_alloc, self.prev_action, r_max=self.r_max_mbps
        )
        self.dt_mgr.record_feedback(reward_breakdown.total_reward, rec.system_state)
        self.prev_action = safe_alloc.copy()

        # Termination
        terminated = self.current_step >= self.max_steps
        truncated = False

        obs = self._build_observation(rec.system_state, packets)
        info = {
            "reward_breakdown": reward_breakdown,
            "safety_override_applied": override_applied,
            "system_state": rec.system_state,
            "allocations": safe_alloc
        }

        return obs, reward_breakdown.total_reward, terminated, truncated, info
