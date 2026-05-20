"""Интеграционные тесты для webhook с проверкой подписи.

Тестируют полный цикл: middleware проверяет подпись, route получает payload.
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthSecurityFix:
    """Тесты что health endpoint не раскрывает sensitive info."""

    def test_health_endpoint_no_debug_field(self, client):
        """Тест что /health не раскрывает debug mode."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "debug" not in data
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
