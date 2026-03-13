"""Tests for health and metrics endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    def test_health_check(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "debug" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "response_time_ms" in data["checks"]


class TestReadyEndpoint:
    def test_readiness_check(self, test_client):
        response = test_client.get("/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_readiness_check_configuration(self, test_client):
        response = test_client.get("/ready")
        data = response.json()
        if data["status"] == "ready":
            assert data["checks"]["database"] == "ok"
            assert data["checks"]["configuration"] == "ok"


class TestMetricsEndpoint:
    def test_metrics_endpoint(self, test_client):
        response = test_client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        content = response.text
        assert "http_requests_total" in content or "python_info" in content

    def test_metrics_format(self, test_client):
        response = test_client.get("/metrics")
        content = response.text
        lines = content.split("\n")
        metric_lines = [l for l in lines if l and not l.startswith("#")]
        assert len(metric_lines) > 0
