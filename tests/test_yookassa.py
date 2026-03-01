import pytest
from unittest.mock import patch, MagicMock
import asyncio
from app.payment_gateways.yookassa import (
    generate_signature,
    verify_signature,
    handle_yookassa_webhook,
)


class TestYookassaSignature:
    def test_generate_signature(self):
        params = {"amount": 1000, "order_id": "123"}
        result = generate_signature(params)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_verify_signature_valid(self):
        params = {"amount": 1000, "order_id": "123"}
        signature = generate_signature(params)
        assert verify_signature(params, signature) is True

    def test_verify_signature_invalid(self):
        params = {"amount": 1000, "order_id": "123"}
        assert verify_signature(params, "invalid_signature") is False


@pytest.mark.asyncio
class TestYookassaWebhook:
    @patch("app.payment_gateways.yookassa.verify_signature", return_value=True)
    async def test_payment_succeeded(self, mock_verify):
        payload = {"event": "payment.succeeded", "payment_id": "123"}
        result = await handle_yookassa_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment successful"

    @patch("app.payment_gateways.yookassa.verify_signature", return_value=True)
    async def test_payment_canceled(self, mock_verify):
        payload = {"event": "payment.canceled", "payment_id": "123"}
        result = await handle_yookassa_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment canceled"

    @patch("app.payment_gateways.yookassa.verify_signature", return_value=False)
    async def test_invalid_signature(self, mock_verify):
        payload = {"event": "payment.succeeded"}
        result = await handle_yookassa_webhook(payload, "sig")
        assert result["status"] == "failed"
        assert result["message"] == "Invalid signature"

    @patch("app.payment_gateways.yookassa.verify_signature", return_value=True)
    async def test_unknown_event(self, mock_verify):
        payload = {"event": "payment.unknown"}
        result = await handle_yookassa_webhook(payload, "sig")
        assert result["status"] == "ignored"
