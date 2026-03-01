import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


class TestWebhookRoutes:
    @patch("app.routes.webhook_routes.process_webhook")
    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_yookassa_webhook(self, mock_verify, mock_process, test_client):
        mock_process.return_value = (
            {"status": "processed", "message": "Payment successful"},
            "order_123",
        )

        response = test_client.post(
            "/webhooks/yookassa",
            json={"event": "payment.succeeded", "payment_id": "123"},
            headers={"X-Signature": "sig123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "Payment successful" in data["message"]

    @patch("app.routes.webhook_routes.process_webhook")
    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_tinkoff_webhook(self, mock_verify, mock_process, test_client):
        mock_process.return_value = (
            {"status": "processed", "message": "Payment successful"},
            "order_456",
        )

        response = test_client.post(
            "/webhooks/tinkoff",
            json={"event": "payment.succeeded", "payment_id": "456"},
            headers={"X-Signature": "sig456"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.routes.webhook_routes.process_webhook")
    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_cloudpayments_webhook(self, mock_verify, mock_process, test_client):
        mock_process.return_value = (
            {"status": "processed", "message": "Payment successful"},
            "order_789",
        )

        response = test_client.post(
            "/webhooks/cloudpayments",
            json={"event": "payment.succeeded", "token": "token123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.routes.webhook_routes.process_webhook")
    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_unitpay_webhook(self, mock_verify, mock_process, test_client):
        mock_process.return_value = (
            {"status": "processed", "message": "Payment successful"},
            "order_abc",
        )

        response = test_client.post(
            "/webhooks/unitpay",
            json={"event": "payment.succeeded"},
            headers={"X-Signature": "sigabc"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.routes.webhook_routes.process_webhook")
    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_robokassa_webhook(self, mock_verify, mock_process, test_client):
        mock_process.return_value = (
            {"status": "processed", "message": "Payment successful"},
            "order_xyz",
        )

        response = test_client.post(
            "/webhooks/robokassa",
            json={"event": "payment.succeeded"},
            headers={"X-Signature": "sigxyz"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch("app.routes.webhook_routes.verify_webhook_ip")
    def test_webhook_invalid_signature(self, mock_verify, test_client):
        with patch(
            "app.routes.webhook_routes.handle_yookassa_webhook",
            return_value={"status": "failed", "message": "Invalid signature"},
        ):
            response = test_client.post(
                "/webhooks/yookassa",
                json={"event": "payment.succeeded"},
                headers={"X-Signature": "invalid"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Invalid signature" in data["message"]
