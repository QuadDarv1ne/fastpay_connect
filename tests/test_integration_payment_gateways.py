"""Integration tests with mocked payment gateways using respx."""

import pytest
import respx
import httpx
from httpx import Response
from fastapi.testclient import TestClient
from app.main import app
from app.settings import settings


@pytest.fixture
def test_client():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_yookassa_settings():
    settings.yookassa_api_key = "test_api_key"
    settings.yookassa_secret_key = "test_secret_key"
    yield
    settings.yookassa_api_key = None
    settings.yookassa_secret_key = None


@pytest.fixture
def mock_tinkoff_settings():
    settings.tinkoff_api_key = "test_api_key"
    settings.tinkoff_secret_key = "test_secret_key"
    yield
    settings.tinkoff_api_key = None
    settings.tinkoff_secret_key = None


@pytest.fixture
def mock_robokassa_settings():
    settings.robokassa_api_key = "test_login"
    settings.robokassa_secret_key = "test_secret"
    yield
    settings.robokassa_api_key = None
    settings.robokassa_secret_key = None


@pytest.fixture
def mock_unitpay_settings():
    settings.unitpay_api_key = "test_project_id"
    settings.unitpay_secret_key = "test_secret"
    yield
    settings.unitpay_api_key = None
    settings.unitpay_secret_key = None


@pytest.fixture
def mock_cloudpayments_settings():
    settings.cloudpayments_api_key = "test_api_key"
    settings.cloudpayments_secret_key = "test_secret"
    yield
    settings.cloudpayments_api_key = None
    settings.cloudpayments_secret_key = None


class TestYookassaIntegration:
    def test_create_payment_success(self, test_client, mock_yookassa_settings):
        yookassa_response = {
            "id": "yookassa_123456",
            "status": "pending",
            "confirmation": {
                "type": "redirect",
                "confirmation_url": "https://yookassa.ru/confirmation/123456",
            },
            "amount": {"value": "1000.00", "currency": "RUB"},
        }
        with respx.mock:
            respx.post("https://api.yookassa.ru/v3/payments").mock(
                return_value=Response(200, json=yookassa_response)
            )

            response = test_client.post(
                "/payments/yookassa",
                json={"amount": 1000.0, "description": "Оплата заказа"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "yookassa_123456"
        assert "confirmation" in data["payment_url"] or "yookassa" in data["payment_url"].lower()

    def test_create_payment_api_error(self, test_client, mock_yookassa_settings):
        with respx.mock:
            respx.post("https://api.yookassa.ru/v3/payments").mock(
                return_value=Response(400, json={"error": "Invalid request"})
            )

            response = test_client.post(
                "/payments/yookassa",
                json={"amount": 1000.0, "description": "Оплата заказа"},
            )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data.get("detail", "") or data.get("detail")

    def test_create_payment_timeout(self, test_client, mock_yookassa_settings):
        """Test timeout handling with retry logic."""
        with respx.mock:
            respx.post("https://api.yookassa.ru/v3/payments").mock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            response = test_client.post(
                "/payments/yookassa",
                json={"amount": 1000.0, "description": "Оплата заказа"},
            )

        assert response.status_code in [400, 503, 504]


class TestTinkoffIntegration:
    def test_create_payment_success(self, test_client, mock_tinkoff_settings):
        tinkoff_response = {
            "payment_id": "tinkoff_789012",
            "status": "NEW",
            "payment_url": "https://tinkoff.ru/pay/789012",
            "amount": 1000,
        }
        with respx.mock:
            respx.post("https://api.tinkoff.ru/v2/payments").mock(
                return_value=Response(200, json=tinkoff_response)
            )

            response = test_client.post(
                "/payments/tinkoff",
                json={"amount": 1000.0, "description": "Оплата курса"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "tinkoff_789012"
        assert data["payment_url"] == "https://tinkoff.ru/pay/789012"

    def test_create_payment_api_error(self, test_client, mock_tinkoff_settings):
        with respx.mock:
            respx.post("https://api.tinkoff.ru/v2/payments").mock(
                return_value=Response(403, json={"errorCode": "INVALID_TOKEN"})
            )

            response = test_client.post(
                "/payments/tinkoff",
                json={"amount": 1000.0, "description": "Оплата курса"},
            )

        assert response.status_code in [400, 503]


class TestRobokassaIntegration:
    def test_create_payment_success(self, test_client, mock_robokassa_settings):
        robokassa_response = {
            "invoice_id": "robokassa_inv_123",
            "redirect_url": "https://robokassa.ru/pay/inv_123",
        }
        with respx.mock:
            respx.post("https://api.robokassa.ru/payment").mock(
                return_value=Response(200, json=robokassa_response)
            )

            response = test_client.post(
                "/payments/robokassa",
                json={"amount": 1000.0, "description": "Оплата услуги"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "robokassa_inv_123"


class TestUnitpayIntegration:
    def test_create_payment_success(self, test_client, mock_unitpay_settings):
        unitpay_response = {
            "payment_id": "unitpay_pay_456",
            "redirect_url": "https://unitpay.ru/pay/456",
        }
        with respx.mock:
            respx.post("https://unitpay.ru/api/payment").mock(
                return_value=Response(200, json=unitpay_response)
            )

            response = test_client.post(
                "/payments/unitpay",
                json={"amount": 500.0, "description": "Покупка"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestCloudPaymentsIntegration:
    def test_create_payment_success(self, test_client, mock_cloudpayments_settings):
        cloudpayments_response = {
            "transaction_id": "cp_txn_789",
            "success": True,
        }
        with respx.mock:
            respx.post("https://api.cloudpayments.ru/payments").mock(
                return_value=Response(200, json=cloudpayments_response)
            )

            response = test_client.post(
                "/payments/cloudpayments",
                json={"amount": 1500.0, "description": "Подписка"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["payment_id"] == "cp_txn_789"


class TestPaymentValidation:
    def test_invalid_amount_negative(self, test_client):
        response = test_client.post(
            "/payments/yookassa",
            json={"amount": -100.0, "description": "Тест"},
        )
        assert response.status_code == 422

    def test_invalid_amount_zero(self, test_client):
        response = test_client.post(
            "/payments/tinkoff",
            json={"amount": 0, "description": "Тест"},
        )
        assert response.status_code == 422

    def test_invalid_amount_too_large(self, test_client):
        response = test_client.post(
            "/payments/robokassa",
            json={"amount": 2000000.0, "description": "Тест"},
        )
        assert response.status_code == 422

    def test_empty_description(self, test_client):
        response = test_client.post(
            "/payments/unitpay",
            json={"amount": 100.0, "description": ""},
        )
        assert response.status_code == 422

    def test_missing_required_fields(self, test_client):
        response = test_client.post(
            "/payments/cloudpayments",
            json={"amount": 100.0},
        )
        assert response.status_code == 422
