"""
Unit and Integration Tests for Edge Service & Monitoring (Phase 9)
Tests FastAPI REST APIs and Metrics Exporter.
"""

import pytest
from fastapi.testclient import TestClient

from cogninet.edge_service.app import app
from cogninet.monitoring.metrics_exporter import MetricsExporter

client = TestClient(app)

def test_edge_service_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "cogninet-6g-edge"
    assert data["models_loaded"]["traffic_predictor"] is True
    assert data["models_loaded"]["semantic_classifier"] is True

def test_edge_service_state():
    response = client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert "current_time" in data
    assert "current_allocations" in data

def test_edge_service_predict():
    # Submit rolling history of shape (10, 4)
    dummy_hist = [[1.5, 0.2, 0.001, 0.1] for _ in range(10)]
    response = client.post("/predict", json={"history": dummy_hist})
    assert response.status_code == 200
    data = response.json()
    assert "predicted_state" in data
    assert len(data["predicted_state"]) == 4
    assert data["inference_time_ms"] < 25.0

def test_edge_service_classify():
    packets = [
        {
            "robot_id": "r01",
            "task_type": "EMERGENCY_STOP",
            "urgency": 1.0,
            "is_critical": True,
            "flow_type": "URLLC",
            "payload_bytes": 128
        },
        {
            "robot_id": "r02",
            "task_type": "TELEMETRY",
            "urgency": 0.2,
            "is_critical": False,
            "flow_type": "mMTC",
            "payload_bytes": 512
        }
    ]
    response = client.post("/classify", json={"packets": packets})
    assert response.status_code == 200
    data = response.json()
    assert "weights" in data
    assert "r01" in data["weights"]
    assert "r02" in data["weights"]
    # Emergency stop must have higher semantic weight than telemetry
    assert data["weights"]["r01"] > data["weights"]["r02"]
    assert data["inference_time_ms"] < 10.0

def test_edge_service_allocate():
    req = {
        "state_vec": [2.0, 0.3, 0.002, 0.15],
        "predicted_state": [2.1, 0.35, 0.002, 0.16],
        "weights": {"r01": 0.95, "r02": 0.2, "r03": 0.2},
        "current_allocations": {"r01": 10.0, "r02": 10.0, "r03": 10.0}
    }
    response = client.post("/allocate", json=req)
    assert response.status_code == 200
    data = response.json()
    assert "allocations" in data
    allocs = data["allocations"]
    assert sum(allocs.values()) <= 100.01
    # Critical robot r01 (w=0.95 >= 0.85) must have >= 15 Mbps guaranteed
    assert allocs["r01"] >= 14.99

def test_edge_service_decision_step():
    response = client.post("/decision")
    assert response.status_code == 200
    data = response.json()
    assert "step" in data
    assert "allocations" in data
    assert "reward" in data
    assert "timing_ms" in data

def test_metrics_exporter():
    exporter = MetricsExporter(prefix="cogninet")
    sample_record = {
        "timestamp": 12.5,
        "state": [1.5, 0.2, 0.001, 0.08],
        "reward": -0.05,
        "sla_violations": 0,
        "safety_override_applied": False,
        "reconfig_cost": 0.02,
        "allocations": {"r01": 20.0, "r02": 10.0},
        "weights": {"r01": 0.8, "r02": 0.3},
        "timing_ms": {"total_loop_ms": 3.5, "decision_ms": 1.2}
    }

    influx_lines = exporter.to_influxdb_line(sample_record)
    assert "cogninet_system_metrics" in influx_lines
    assert "cogninet_robot_metrics,robot_id=r01" in influx_lines

    prom_text = exporter.to_prometheus_text(sample_record)
    assert "cogninet_latency_ms 1.5000" in prom_text
    assert 'cogninet_bandwidth_mbps{robot_id="r01"} 20.0000' in prom_text
