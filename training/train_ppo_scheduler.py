"""
Training Pipeline for PPO Network Slicing Scheduler (Module 140)
Trains a Stable-Baselines3 PPO agent in CogniNetSlicingEnv with deterministic safety layer.
"""

import os
import sys
import json
import yaml
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from cogninet.scheduler.gym_env import CogniNetSlicingEnv
from experiments.scenarios.traffic_generator import Scenario

class RewardLoggingCallback(BaseCallback):
    def __init__(self, check_freq: int = 1000):
        super().__init__()
        self.check_freq = check_freq
        self.episode_rewards = []
        self.current_ep_reward = 0.0

    def _on_step(self) -> bool:
        reward = self.locals["rewards"][0]
        self.current_ep_reward += reward
        dones = self.locals["dones"]
        if dones[0]:
            self.episode_rewards.append(self.current_ep_reward)
            self.current_ep_reward = 0.0
        return True

def main():
    print("==================================================================")
    print("      CogniNet-6G Phase 7: Training PPO Network Slicing Policy    ")
    print("==================================================================\n")

    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    pred_path = os.path.join(models_dir, "lstm_predictor.pt")
    sem_path = os.path.join(models_dir, "semantic_classifier.pt")

    env = CogniNetSlicingEnv(
        config=config,
        scenario=Scenario.B_CONGESTION_BURST,
        max_steps=60,
        enable_safety_override=True,
        predictor_weights_path=pred_path if os.path.exists(pred_path) else None,
        semantic_weights_path=sem_path if os.path.exists(sem_path) else None,
        random_seed=42
    )

    ppo_cfg = config.get("models", {}).get("ppo", {})
    model = PPO(
        policy="MlpPolicy",
        env=env,
        learning_rate=ppo_cfg.get("learning_rate", 0.0003),
        n_steps=1024,
        batch_size=64,
        n_epochs=10,
        gamma=ppo_cfg.get("gamma", 0.99),
        clip_range=ppo_cfg.get("clip_range", 0.2),
        ent_coef=ppo_cfg.get("ent_coef", 0.01),
        verbose=1,
        seed=42
    )

    callback = RewardLoggingCallback(check_freq=1000)
    total_timesteps = 12000
    print(f"[*] Training PPO agent for {total_timesteps} timesteps...")
    model.learn(total_timesteps=total_timesteps, callback=callback)

    # Save Checkpoint
    model_save_path = os.path.join(models_dir, "ppo_scheduler.zip")
    model.save(model_save_path)
    print(f"\n[+] Saved PPO policy checkpoint to {model_save_path}")

    # Evaluate on fresh episode
    obs, _ = env.reset(seed=123)
    eval_rewards = []
    overrides = 0
    done = False
    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, r, terminated, truncated, info = env.step(action)
        eval_rewards.append(r)
        if info.get("safety_override_applied", False):
            overrides += 1
        done = terminated or truncated

    eval_summary = {
        "total_timesteps": total_timesteps,
        "mean_eval_reward": round(float(sum(eval_rewards) / len(eval_rewards)), 4),
        "safety_overrides_applied": overrides,
        "final_state": info.get("system_state", [])
    }
    eval_path = os.path.join(REPO_ROOT, "results", "tables", "ppo_training_summary.json")
    with open(eval_path, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)
    print(f"[+] Saved PPO evaluation summary to {eval_path}\n")

if __name__ == "__main__":
    main()
