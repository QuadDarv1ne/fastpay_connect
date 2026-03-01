import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from sqlalchemy.orm import Session


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


class TestPaymentRoutes:
    @patch("app.routes.payment_routes.create_payment_record")
    @patch("app.routes.payment_routes.yookassa_create")
    def test_create_yookassa_payment(self, mock_yookassa, mock_create_record, test_client):
        mock_payment = MagicMock()
        mock_payment.payment_id = None
        mock_payment.payment_url = None
        mock_payment.status = "pending"
        mock_create_record.return_value = mock_payment

        mock_yookassa.return_value = {
            "id": "yookassa_123",
            "confirmation": {"confirmation_url": "https://yookassa.ru/pay/123"}
        }

        response = test_client.post(
            "/payments/yookassa",
            json={
                "amount": 1000.0,
                "description": "Оплата заказа"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "yookassa_123"
        assert data["payment_url"] == "https://yookassa.ru/pay/123"

    @patch("app.routes.payment_routes.create_payment_record")
    @patch("app.routes.payment_routes.tinkoff_create")
    def test_create_tinkoff_payment(self, mock_tinkoff, mock_create_record, test_client):
        mock_payment = MagicMock()
        mock_payment.payment_id = None
        mock_payment.payment_url = None
        mock_payment.status = "pending"
        mock_create_record.return_value = mock_payment

        mock_tinkoff.return_value = {
            "payment_id": "tinkoff_456",
            "payment_url": "https://tinkoff.ru/pay/456"
        }

        response = test_client.post(
            "/payments/tinkoff",
            json={
                "amount": 2000.0,
                "description": "Оплата курса"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "tinkoff_456"

    @patch("app.routes.payment_routes.create_payment_record")
    @patch("app.routes.payment_routes.cloudpayments_create")
    def test_create_cloudpayments_payment(self, mock_cp, mock_create_record, test_client):
        mock_payment = MagicMock()
        mock_payment.payment_id = None
        mock_payment.payment_url = None
        mock_payment.status = "pending"
        mock_create_record.return_value = mock_payment

        mock_cp.return_value = {
            "transaction_id": "cp_789"
        }

        response = test_client.post(
            "/payments/cloudpayments",
            json={
                "amount": 1500.0,
                "description": "Подписка"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "cp_789"

    @patch("app.routes.payment_routes.create_payment_record")
    @patch("app.routes.payment_routes.unitpay_create")
    def test_create_unitpay_payment(self, mock_unitpay, mock_create_record, test_client):
        mock_payment = MagicMock()
        mock_payment.payment_id = None
        mock_payment.payment_url = None
        mock_payment.status = "pending"
        mock_create_record.return_value = mock_payment

        mock_unitpay.return_value = {
            "payment_id": "unitpay_abc"
        }

        response = test_client.post(
            "/payments/unitpay",
            json={
                "amount": 500.0,
                "description": "Покупка"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("app.routes.payment_routes.create_payment_record")
    @patch("app.routes.payment_routes.robokassa_create")
    def test_create_robokassa_payment(self, mock_robokassa, mock_create_record, test_client):
        mock_payment = MagicMock()
        mock_payment.payment_id = None
        mock_payment.payment_url = None
        mock_payment.status = "pending"
        mock_create_record.return_value = mock_payment

        mock_robokassa.return_value = {
            "invoice_id": "robokassa_xyz"
        }

        response = test_client.post(
            "/payments/robokassa",
            json={
                "amount": 1200.0,
                "description": "Услуга"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_invalid_amount(self, test_client):
        response = test_client.post(
            "/payments/yookassa",
            json={
                "amount": 0,
                "description": "Тест"
            }
        )
        assert response.status_code == 422

    def test_missing_description(self, test_client):
        response = test_client.post(
            "/payments/tinkoff",
            json={
                "amount": 1000.0
            }
        )
        assert response.status_code == 422
