"""
API tests for OpsLens FastAPI endpoints using TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "OpsLens"
    assert data["status"] == "online"


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "critical")
    assert "exasol_version" in data
    assert "reference_clock" in data
    assert "avg_trust_score" in data


def test_get_runs():
    response = client.get("/api/runs?days=7")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert "run_id" in first
    assert "job_id" in first
    assert "stage" in first
    assert "status" in first


def test_get_alerts():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_trust():
    response = client.get("/api/trust")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 8
    first = data[0]
    assert "object_name" in first
    assert "trust_score" in first
    assert "status" in first


def test_get_trust_history():
    response = client.get("/api/trust/history?days=7")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_lineage():
    response = client.get("/api/lineage")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


def test_get_blast_radius():
    response = client.get("/api/lineage/blast-radius?node_id=OPSLENS.ORDERS")
    assert response.status_code == 200
    data = response.json()
    assert "affected_nodes" in data
    assert "affected_dashboards" in data


def test_get_timeline():
    response = client.get("/api/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_cost_radar():
    response = client.get("/api/cost-radar")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "team_breakdown" in data
    assert "top_expensive_queries" in data
    assert "cold_unused_tables" in data
    assert data["summary"]["total_queries"] >= 1000


def test_get_baselines():
    response = client.get("/api/baselines")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 10
