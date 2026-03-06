import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealthCheck:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "debug" in data

    def test_ready_endpoint(self, client):
        response = client.get("/ready")
        assert response.status_code in (200, 503)
        assert "status" in response.json()
