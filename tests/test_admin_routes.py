import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_payment_repository
from datetime import datetime, timezone


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def admin_headers():
    """Заголовки для admin endpoints с API key."""
    return {"x-api-key": "test_api_key_for_admin_access_minimum_32_chars"}


def create_mock_repository():
    """Создание мок репозитория."""
    mock_repo = MagicMock()
    mock_payment = MagicMock()
    mock_payment.order_id = "order_123"
    mock_payment.payment_id = "pay_123"
    mock_payment.payment_gateway = "yookassa"
    mock_payment.amount = 1000.0
    mock_payment.currency = "RUB"
    mock_payment.status = "pending"
    mock_payment.description = "Test"
    mock_payment.created_at = datetime.now(timezone.utc)
    mock_payment.updated_at = datetime.now(timezone.utc)
    mock_repo.get_by_order_id.return_value = mock_payment
    mock_repo.get_by_status.return_value = [mock_payment]
    mock_repo.get_by_gateway.return_value = [mock_payment]
    mock_repo.update_status.return_value = mock_payment
    mock_repo.get_statistics.return_value = {
        "total_payments": 100,
        "by_status": {"pending": 10, "completed": 80, "failed": 10},
        "by_gateway": {"yookassa": 50, "tinkoff": 50},
        "total_completed_amount": 100000.0,
    }
    mock_repo.get_by_status_paginated.return_value = ([mock_payment], 1)
    mock_repo.get_by_gateway_paginated.return_value = ([mock_payment], 1)
    return mock_repo


class TestAdminRoutes:
    def test_get_payment(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.get("/admin/payments/order_123", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_123"
        assert data["payment_gateway"] == "yookassa"

        app.dependency_overrides.clear()

    def test_get_payment_not_found(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        mock_repo.get_by_order_id.return_value = None
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.get("/admin/payments/nonexistent", headers=admin_headers)

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_get_payments_by_status(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.get("/admin/payments/status/pending", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

        app.dependency_overrides.clear()

    def test_get_payments_by_gateway(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.get("/admin/payments/gateway/yookassa", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1

        app.dependency_overrides.clear()

    def test_refund_payment(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.post(
            "/admin/payments/refund",
            json={"order_id": "order_123", "reason": "Customer request"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        app.dependency_overrides.clear()

    def test_refund_payment_missing_id(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.post(
            "/admin/payments/refund",
            json={},
            headers=admin_headers,
        )

        assert response.status_code == 400

        app.dependency_overrides.clear()

    def test_refund_payment_not_found(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        mock_repo.update_status.return_value = None
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.post(
            "/admin/payments/refund",
            json={"order_id": "nonexistent"},
            headers=admin_headers,
        )

        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_cancel_payment(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.post(
            "/admin/payments/cancel",
            json={"order_id": "order_123", "reason": "Customer request"},
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        app.dependency_overrides.clear()

    def test_cancel_payment_missing_id(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.post(
            "/admin/payments/cancel",
            json={},
            headers=admin_headers,
        )

        assert response.status_code == 400

        app.dependency_overrides.clear()

    def test_get_statistics(self, test_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = test_client.get("/admin/payments/statistics", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_payments"] == 100

        app.dependency_overrides.clear()
