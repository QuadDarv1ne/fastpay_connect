import pytest
from app.payment_gateways.base import BasePaymentGateway


class ConcreteGateway(BasePaymentGateway):
    """Concrete implementation for testing."""

    def create_payment(self, amount: float, description: str, order_id: str):
        return {"status": "created"}

    async def handle_webhook(self, payload: dict, signature: str):
        return {"status": "processed"}


class TestBasePaymentGateway:
    @pytest.fixture
    def gateway(self):
        return ConcreteGateway(
            api_key="test_api_key",
            secret_key="test_secret_key",
            return_url="https://example.com/return",
            base_url="https://api.example.com",
        )

    def test_init(self, gateway):
        assert gateway.api_key == "test_api_key"
        assert gateway.secret_key == "test_secret_key"
        assert gateway.return_url == "https://example.com/return"
        assert gateway.base_url == "https://api.example.com"

    def test_generate_signature(self, gateway):
        params = {"amount": 1000, "order_id": "123"}
        signature = gateway.generate_signature(params)
        assert isinstance(signature, str)
        assert len(signature) == 64

    def test_verify_signature_valid(self, gateway):
        params = {"amount": 1000, "order_id": "123"}
        signature = gateway.generate_signature(params)
        assert gateway.verify_signature(params, signature) is True

    def test_verify_signature_invalid(self, gateway):
        params = {"amount": 1000, "order_id": "123"}
        assert gateway.verify_signature(params, "invalid") is False

    def test_validate_config_pass(self, gateway):
        assert gateway.validate_config() is True

    def test_validate_config_fail_no_api_key(self):
        gateway = ConcreteGateway(
            api_key=None,
            secret_key="test_secret",
            return_url="https://example.com",
            base_url="https://api.example.com",
        )
        assert gateway.validate_config() is False

    def test_generate_signature_no_secret_key(self, caplog):
        gateway = ConcreteGateway(
            api_key="test_api_key",
            secret_key=None,
            return_url="https://example.com",
            base_url="https://api.example.com",
        )
        signature = gateway.generate_signature({"key": "value"})
        assert signature == ""
        assert "secret key not configured" in caplog.text
