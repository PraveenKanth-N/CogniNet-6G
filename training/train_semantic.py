"""
Training & Evaluation Pipeline for Semantic Priority Classifier (Module 130)
Generates representative industrial packet metadata, trains the lightweight MLP
with cost-sensitive loss (penalizing critical false negatives), and benchmarks inference latency.
"""

import os
import sys
import json
import time
import random
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from cogninet.semantic.classifier import LightweightSemanticClassifier
from cogninet.semantic.taxonomy import SemanticClass

def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def generate_synthetic_metadata_dataset(num_samples: int = 5000, seed: int = 42):
    """
    Synthesizes realistic industrial robot message metadata vectors:
    [task_idx, urgency, is_critical, payload_norm, speed, dist_obs, batt, zone]
    Class labels: 0=CRITICAL, 1=HIGH, 2=MEDIUM, 3=LOW
    """
    rng = np.random.RandomState(seed)
    X = []
    Y = []

    samples_per_class = num_samples // 4

    # Class 0: CRITICAL (Emergency Stop, Collision Avoidance)
    for _ in range(samples_per_class):
        task_idx = 0.0 + rng.normal(0, 0.02)
        urgency = rng.uniform(0.90, 1.0)
        is_crit = 1.0
        payload_norm = rng.uniform(0.001, 0.02)
        speed = rng.uniform(0.0, 1.0)
        dist_obs = rng.uniform(0.0, 0.2)  # Close to obstacle!
        batt = rng.uniform(0.2, 1.0)
        zone = rng.uniform(0.0, 1.0)
        X.append([task_idx, urgency, is_crit, payload_norm, speed, dist_obs, batt, zone])
        Y.append(0)

    # Class 1: HIGH (Navigation updates, trajectory correction)
    for _ in range(samples_per_class):
        task_idx = 0.25 + rng.normal(0, 0.02)
        urgency = rng.uniform(0.70, 0.88)
        is_crit = 0.0
        payload_norm = rng.uniform(0.005, 0.05)
        speed = rng.uniform(0.4, 1.0)
        dist_obs = rng.uniform(0.2, 0.6)
        batt = rng.uniform(0.3, 1.0)
        zone = rng.uniform(0.0, 1.0)
        X.append([task_idx, urgency, is_crit, payload_norm, speed, dist_obs, batt, zone])
        Y.append(1)

    # Class 2: MEDIUM (Mission synchronization, inspection video)
    for _ in range(samples_per_class):
        task_idx = 0.50 if rng.rand() < 0.5 else 0.75
        urgency = rng.uniform(0.35, 0.65)
        is_crit = 0.0
        payload_norm = rng.uniform(0.1, 1.0) if task_idx > 0.6 else rng.uniform(0.02, 0.1)
        speed = rng.uniform(0.0, 0.5)
        dist_obs = rng.uniform(0.5, 1.0)
        batt = rng.uniform(0.4, 1.0)
        zone = rng.uniform(0.0, 1.0)
        X.append([task_idx, urgency, is_crit, payload_norm, speed, dist_obs, batt, zone])
        Y.append(2)

    # Class 3: LOW (Routine periodic telemetry, battery status)
    for _ in range(samples_per_class):
        task_idx = 1.0 + rng.normal(0, 0.02)
        urgency = rng.uniform(0.05, 0.30)
        is_crit = 0.0
        payload_norm = rng.uniform(0.005, 0.02)
        speed = rng.uniform(0.0, 0.8)
        dist_obs = rng.uniform(0.6, 1.0)
        batt = rng.uniform(0.1, 1.0)
        zone = rng.uniform(0.0, 1.0)
        X.append([task_idx, urgency, is_crit, payload_norm, speed, dist_obs, batt, zone])
        Y.append(3)

    X = np.array(X, dtype=np.float32)
    Y = np.array(Y, dtype=np.int64)

    # Shuffle
    indices = rng.permutation(len(X))
    return X[indices], Y[indices]

def benchmark_inference_latency(model: nn.Module, device: torch.device, num_iterations: int = 10000) -> float:
    """Measures average per-packet inference latency in microseconds."""
    model.eval()
    dummy_input = torch.randn(1, 8, device=device)
    # Warmup
    for _ in range(100):
        with torch.no_grad():
            _ = model(dummy_input)

    if device.type == "cuda":
        torch.cuda.synchronize()

    t_start = time.perf_counter()
    with torch.no_grad():
        for _ in range(num_iterations):
            _ = model(dummy_input)
    if device.type == "cuda":
        torch.cuda.synchronize()
    t_total = time.perf_counter() - t_start

    avg_latency_us = (t_total / num_iterations) * 1e6
    return avg_latency_us

def main():
    print("==================================================================")
    print("      CogniNet-6G Phase 6: Training Semantic Priority Classifier  ")
    print("==================================================================\n")

    set_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[*] Training device: {device}")

    X, Y = generate_synthetic_metadata_dataset(num_samples=6000, seed=42)
    n_total = len(X)
    n_train = int(0.70 * n_total)
    n_val = int(0.15 * n_total)

    X_train, Y_train = X[:n_train], Y[:n_train]
    X_val, Y_val = X[n_train : n_train + n_val], Y[n_train : n_train + n_val]
    X_test, Y_test = X[n_train + n_val :], Y[n_train + n_val :]

    train_loader = DataLoader(TensorDataset(torch.from_numpy(X_train), torch.from_numpy(Y_train)), batch_size=64, shuffle=True)
    val_loader = DataLoader(TensorDataset(torch.from_numpy(X_val), torch.from_numpy(Y_val)), batch_size=64, shuffle=False)

    # Cost-sensitive loss weights: [Class 0 (Critical)=10.0, Class 1=2.0, Class 2=1.0, Class 3=1.0]
    class_loss_weights = torch.tensor([10.0, 2.0, 1.0, 1.0], dtype=torch.float32, device=device)
    criterion = nn.CrossEntropyLoss(weight=class_loss_weights)

    model = LightweightSemanticClassifier(input_dim=8, hidden_dim=32, num_classes=4).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=1e-4)

    best_val_loss = float("inf")
    best_weights = None

    for epoch in range(25):
        model.train()
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            logits, _ = model(bx)
            loss = criterion(logits, by)
            loss.backward()
            optimizer.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                logits, _ = model(bx)
                val_loss += criterion(logits, by).item() * bx.size(0)

        val_loss /= len(X_val)
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_weights = model.state_dict().copy()

    model.load_state_dict(best_weights)

    # Test Evaluation
    model.eval()
    test_tensor = torch.from_numpy(X_test).to(device)
    with torch.no_grad():
        test_logits, _ = model(test_tensor)
        y_pred = torch.argmax(test_logits, dim=-1).cpu().numpy()

    acc = float(accuracy_score(Y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(Y_test, y_pred, average="weighted", zero_division=0)
    cm = confusion_matrix(Y_test, y_pred).tolist()

    # Specifically measure critical recall (Class 0)
    crit_mask = (Y_test == 0)
    crit_recall = float(np.sum((y_pred == 0) & crit_mask) / np.sum(crit_mask))
    crit_fnr = 1.0 - crit_recall

    # Latency Benchmark
    latency_us = benchmark_inference_latency(model, device, num_iterations=10000)
    latency_ms = latency_us / 1000.0

    print(f"[+] Overall Test Accuracy: {round(acc * 100, 2)}%")
    print(f"[+] Weighted F1 Score: {round(f1, 4)}")
    print(f"[+] Critical Class Recall: {round(crit_recall * 100, 2)}% (False Negative Rate: {round(crit_fnr * 100, 4)}%)")
    print(f"[+] Inline Inference Latency: {round(latency_us, 2)} μs ({round(latency_ms, 4)} ms)")

    # Save Checkpoint
    models_dir = os.path.join(REPO_ROOT, "configs", "models")
    os.makedirs(models_dir, exist_ok=True)
    model_path = os.path.join(models_dir, "semantic_classifier.pt")
    torch.save(best_weights, model_path)
    print(f"[+] Saved model checkpoint to {model_path}")

    # Save Metrics Summary
    res_dir = os.path.join(REPO_ROOT, "results", "tables")
    os.makedirs(res_dir, exist_ok=True)
    metrics_summary = {
        "dataset_samples": n_total,
        "test_accuracy": round(acc, 4),
        "weighted_precision": round(float(prec), 4),
        "weighted_recall": round(float(rec), 4),
        "weighted_f1": round(float(f1), 4),
        "critical_recall": round(crit_recall, 4),
        "critical_false_negative_rate": round(crit_fnr, 4),
        "confusion_matrix": cm,
        "inference_latency_microseconds": round(latency_us, 2),
        "inference_latency_ms": round(latency_ms, 4)
    }
    with open(os.path.join(res_dir, "semantic_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"[+] Saved semantic metrics summary to {os.path.join(res_dir, 'semantic_metrics.json')}\n")

if __name__ == "__main__":
    main()
