"""
Integration tests for the FastAPI API endpoints.
"""
from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "checkout-service" in data["supported_services"]


def test_trigger_incident_api():
    resp = client.post(
        "/api/incident/trigger",
        json={
            "service": "checkout-service",
            "severity": "P1_CRITICAL",
            "trigger_metric": "error_rate_pct",
            "metric_value": 18.5,
            "description": "Test incident",
            "inject_fault": False,
            "simulate_production_freeze": False
        }
    )
    assert resp.status_code == 200
    traj = resp.json()
    assert traj["status"] == "RESOLVED"
    assert traj["verification_passed"]
    assert len(traj["steps"]) >= 4


def test_trigger_incident_with_fault_injection():
    resp = client.post(
        "/api/incident/trigger",
        json={
            "service": "checkout-service",
            "severity": "P1_CRITICAL",
            "trigger_metric": "error_rate_pct",
            "metric_value": 18.5,
            "description": "Fault test",
            "inject_fault": True,
            "simulate_production_freeze": False
        }
    )
    assert resp.status_code == 200
    traj = resp.json()
    assert traj["status"] == "RESOLVED"
    assert traj["transient_retries_performed"] == 2


def test_eval_trajectory_endpoint():
    resp = client.post("/api/eval/trajectory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pass_pow_3_standard"] == 1.0
    assert data["fault_recovery_rate"] == 1.0
