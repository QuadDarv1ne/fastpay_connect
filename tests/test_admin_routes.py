import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timezone


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


class TestAdminRoutes:
    @patch("app.routes.admin_routes.get_payment_by_order_id")
    def test_get_payment(self, mock_get, test_client):
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
        mock_get.return_value = mock_payment

        response = test_client.get("/admin/payments/order_123")

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order_123"
        assert data["payment_gateway"] == "yookassa"

    @patch("app.routes.admin_routes.get_payment_by_order_id")
    def test_get_payment_not_found(self, mock_get, test_client):
        mock_get.return_value = None

        response = test_client.get("/admin/payments/nonexistent")

        assert response.status_code == 404

    @patch("app.routes.admin_routes.get_payments_by_status")
    def test_get_payments_by_status(self, mock_get, test_client):
        mock_payment = MagicMock()
        mock_payment.order_id = "order_1"
        mock_payment.payment_id = "pay_1"
        mock_payment.payment_gateway = "yookassa"
        mock_payment.amount = 1000.0
        mock_payment.currency = "RUB"
        mock_payment.status = "pending"
        mock_payment.description = "Test"
        mock_payment.created_at = datetime.now(timezone.utc)
        mock_payment.updated_at = datetime.now(timezone.utc)
        mock_get.return_value = [mock_payment]

        response = test_client.get("/admin/payments/status/pending")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @patch("app.routes.admin_routes.get_payments_by_gateway")
    def test_get_payments_by_gateway(self, mock_get, test_client):
        mock_payment = MagicMock()
        mock_payment.order_id = "order_1"
        mock_payment.payment_id = "pay_1"
        mock_payment.payment_gateway = "yookassa"
        mock_payment.amount = 1000.0
        mock_payment.currency = "RUB"
        mock_payment.status = "pending"
        mock_payment.description = "Test"
        mock_payment.created_at = datetime.now(timezone.utc)
        mock_payment.updated_at = datetime.now(timezone.utc)
        mock_get.return_value = [mock_payment]

        response = test_client.get("/admin/payments/gateway/yookassa")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @patch("app.routes.admin_routes.refund_payment")
    def test_refund_payment(self, mock_refund, test_client):
        mock_payment = MagicMock()
        mock_payment.order_id = "order_123"
        mock_payment.status = "refunded"
        mock_refund.return_value = mock_payment

        response = test_client.post(
            "/admin/payments/refund",
            json={"order_id": "order_123", "reason": "Customer request"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "refunded" in data["message"].lower()

    @patch("app.routes.admin_routes.refund_payment")
    def test_refund_payment_missing_id(self, mock_refund, test_client):
        response = test_client.post("/admin/payments/refund", json={})

        assert response.status_code == 400

    @patch("app.routes.admin_routes.refund_payment")
    def test_refund_payment_not_found(self, mock_refund, test_client):
        mock_refund.return_value = None

        response = test_client.post(
            "/admin/payments/refund",
            json={"order_id": "nonexistent"},
        )

        assert response.status_code == 404

    @patch("app.routes.admin_routes.cancel_payment")
    def test_cancel_payment(self, mock_cancel, test_client):
        mock_payment = MagicMock()
        mock_payment.order_id = "order_123"
        mock_payment.status = "cancelled"
        mock_cancel.return_value = mock_payment

        response = test_client.post(
            "/admin/payments/cancel",
            json={"order_id": "order_123", "reason": "Customer request"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "cancelled" in data["message"].lower()

    @patch("app.routes.admin_routes.cancel_payment")
    def test_cancel_payment_missing_id(self, mock_cancel, test_client):
        response = test_client.post("/admin/payments/cancel", json={})

        assert response.status_code == 400

    @patch("app.routes.admin_routes.get_payment_statistics")
    def test_get_statistics(self, mock_stats, test_client):
        mock_stats.return_value = {
            "total_payments": 100,
            "by_status": {"pending": 10, "completed": 80, "failed": 10},
            "by_gateway": {"yookassa": 50, "tinkoff": 50},
            "total_completed_amount": 100000.0,
        }

        response = test_client.get("/admin/payments/statistics")

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["total_payments"] == 100
        assert "by_status" in data
        assert "by_gateway" in data
