"""
Offline Training Pipeline for Traffic Prediction Module (120)
Trains primary LSTMTrafficPredictor and comparison TransformerTrafficPredictor
on empirical co-simulation datasets with strict temporal splitting (no data leakage).
"""

import os
import sys
import json
import glob
import math
import random
import yaml
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from cogninet.prediction.lstm import LSTMTrafficPredictor
from cogninet.prediction.transformer_baseline import TransformerTrafficPredictor

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def create_dataset(
    raw_dir: str,
    k_window: int = 10,
    forecast_horizon_steps: int = 4
):
    """
    Constructs sequence pairs (X, Y) from empirical CSV datasets:
    X: [S(t-k), ..., S(t)] shape (k, 4)
    Y: S(t + Delta) shape (4,)
    """
    csv_files = sorted(glob.glob(os.path.join(raw_dir, "*.csv")))
    all_X = []
    all_Y = []

    for f in csv_files:
        df = pd.read_csv(f)
        features = df[["latency_ms", "jitter_ms", "packet_loss_ratio", "resource_utilization"]].values
        n_samples = len(features)

        for i in range(n_samples - k_window - forecast_horizon_steps + 1):
            x_seq = features[i : i + k_window]
            y_target = features[i + k_window + forecast_horizon_steps - 1]
            all_X.append(x_seq)
            all_Y.append(y_target)

    return np.array(all_X, dtype=np.float32), np.array(all_Y, dtype=np.float32)

def evaluate_model(model: nn.Module, loader: DataLoader, device: torch.device, mean: np.ndarray, std: np.ndarray):
    model.eval()
    preds_list = []
    targets_list = []

    with torch.no_grad():
        for batch_x, batch_y in loader:
            batch_x = batch_x.to(device)
            out = model(batch_x)
            preds_list.append(out.cpu().numpy())
            targets_list.append(batch_y.numpy())

    preds = np.vstack(preds_list)
    targets = np.vstack(targets_list)

    # Invert standardization to physical units
    preds_phys = preds * std + mean
    targets_phys = targets * std + mean

    mse = float(np.mean((preds_phys - targets_phys) ** 2))
    rmse = float(math.sqrt(mse))
    mae = float(np.mean(np.abs(preds_phys - targets_phys)))

    # Compute R^2 score
    ss_tot = np.sum((targets_phys - np.mean(targets_phys, axis=0)) ** 2)
    ss_res = np.sum((targets_phys - preds_phys) ** 2)
    r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

    return {
        "mse": round(mse, 4),
        "rmse": round(rmse, 4),
        "mae": round(mae, 4),
        "r2": round(r2, 4)
    }

def main():
    print("==================================================================")
    print("      CogniNet-6G Phase 5: Training Traffic Prediction Models     ")
    print("==================================================================\n")

    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training device: {device}")

    cfg_path = os.path.join(REPO_ROOT, "configs", "simulation", "sim_config.yaml")
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    k_window = config.get("timing", {}).get("history_window_k", 10)
    horizon_s = config.get("timing", {}).get("forecast_horizon", 2.0)
    dt = config.get("timing", {}).get("delta_t", 0.5)
    horizon_steps = int(round(horizon_s / dt))

    raw_dir = os.path.join(REPO_ROOT, "datasets", "raw")
    X, Y = create_dataset(raw_dir, k_window=k_window, forecast_horizon_steps=horizon_steps)
    print(f"[*] Constructed {len(X)} sequential training pairs (k={k_window}, horizon={horizon_steps} steps).")

    # Chronological / Temporal Split: 70% train, 15% val, 15% test
    n_total = len(X)
    n_train = int(0.70 * n_total)
    n_val = int(0.15 * n_total)

    X_train, Y_train = X[:n_train], Y[:n_train]
    X_val, Y_val = X[n_train : n_train + n_val], Y[n_train : n_train + n_val]
    X_test, Y_test = X[n_train + n_val :], Y[n_train + n_val :]

    # Fit feature standardizer on TRAIN partition only (no future data leakage)
    train_feats = X_train.reshape(-1, 4)
    mean = np.mean(train_feats, axis=0)
    std = np.std(train_feats, axis=0) + 1e-6

    # Normalize datasets
    X_train_norm = (X_train - mean) / std
    Y_train_norm = (Y_train - mean) / std
    X_val_norm = (X_val - mean) / std
    Y_val_norm = (Y_val - mean) / std
    X_test_norm = (X_test - mean) / std
    Y_test_norm = (Y_test - mean) / std

    # Save scaler parameters
    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    os.makedirs(models_dir, exist_ok=True)
    scaler_info = {"mean": mean.tolist(), "std": std.tolist(), "feature_names": ["latency_ms", "jitter_ms", "packet_loss_ratio", "resource_utilization"]}
    with open(os.path.join(models_dir, "predictor_scaler.json"), "w", encoding="utf-8") as f:
        json.dump(scaler_info, f, indent=2)

    # DataLoaders
    train_loader = DataLoader(TensorDataset(torch.from_numpy(X_train_norm), torch.from_numpy(Y_train_norm)), batch_size=32, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.from_numpy(X_val_norm), torch.from_numpy(Y_val_norm)), batch_size=32, shuffle=False)
    test_loader = DataLoader(TensorDataset(torch.from_numpy(X_test_norm), torch.from_numpy(Y_test_norm)), batch_size=32, shuffle=False)

    # 1. Train Primary Model: LSTM
    print("\n[*] Training Primary Model: LSTMTrafficPredictor...")
    lstm_model = LSTMTrafficPredictor(input_dim=4, hidden_dim=64, num_layers=2, output_dim=4, dropout=0.1).to(device)
    optimizer_lstm = torch.optim.Adam(lstm_model.parameters(), lr=0.002, weight_decay=1e-5)
    criterion = nn.MSELoss()

    best_val_loss = float("inf")
    best_lstm_weights = None

    for epoch in range(35):
        lstm_model.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer_lstm.zero_grad()
            out = lstm_model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer_lstm.step()
            train_loss += loss.item() * bx.size(0)

        lstm_model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                out = lstm_model(bx)
                val_loss += criterion(out, by).item() * bx.size(0)

        val_loss /= len(X_val)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_lstm_weights = lstm_model.state_dict().copy()

    lstm_model.load_state_dict(best_lstm_weights)
    lstm_metrics = evaluate_model(lstm_model, test_loader, device, mean, std)
    torch.save(best_lstm_weights, os.path.join(models_dir, "lstm_predictor.pt"))
    print(f"    [+] LSTM Test Metrics: MSE={lstm_metrics['mse']}, RMSE={lstm_metrics['rmse']}, MAE={lstm_metrics['mae']}, R2={lstm_metrics['r2']}")

    # 2. Train Comparison Model: Transformer
    print("\n[*] Training Comparison Model: TransformerTrafficPredictor...")
    tf_model = TransformerTrafficPredictor(input_dim=4, d_model=64, nhead=4, num_layers=2, output_dim=4, dropout=0.1).to(device)
    optimizer_tf = torch.optim.Adam(tf_model.parameters(), lr=0.001, weight_decay=1e-5)

    best_tf_val_loss = float("inf")
    best_tf_weights = None

    for epoch in range(35):
        tf_model.train()
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer_tf.zero_grad()
            out = tf_model(bx)
            loss = criterion(out, by)
            loss.backward()
            optimizer_tf.step()

        tf_model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                out = tf_model(bx)
                val_loss += criterion(out, by).item() * bx.size(0)

        val_loss /= len(X_val)
        if val_loss < best_tf_val_loss:
            best_tf_val_loss = val_loss
            best_tf_weights = tf_model.state_dict().copy()

    tf_model.load_state_dict(best_tf_weights)
    tf_metrics = evaluate_model(tf_model, test_loader, device, mean, std)
    torch.save(best_tf_weights, os.path.join(models_dir, "transformer_predictor.pt"))
    print(f"    [+] Transformer Test Metrics: MSE={tf_metrics['mse']}, RMSE={tf_metrics['rmse']}, MAE={tf_metrics['mae']}, R2={tf_metrics['r2']}")

    # Save overall prediction evaluation table
    res_dir = os.path.join(REPO_ROOT, "results", "tables")
    os.makedirs(res_dir, exist_ok=True)
    metrics_summary = {
        "dataset_samples": n_total,
        "k_history_steps": k_window,
        "forecast_horizon_seconds": horizon_s,
        "lstm_primary": lstm_metrics,
        "transformer_comparison": tf_metrics
    }
    with open(os.path.join(res_dir, "prediction_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"\n[+] Saved prediction metrics summary to {os.path.join(res_dir, 'prediction_metrics.json')}\n")

if __name__ == "__main__":
    main()
