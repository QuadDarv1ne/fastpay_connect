import pytest
from app.payment_gateways.tinkoff import gateway, handle_tinkoff_webhook


class TestTinkoffSignature:
    def test_generate_signature(self):
        params = {"amount": 1000, "order_id": "123"}
        result = gateway.generate_signature(params)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_verify_signature_valid(self):
        params = {"amount": 1000, "order_id": "123"}
        signature = gateway.generate_signature(params)
        assert gateway.verify_signature(params, signature) is True

    def test_verify_signature_invalid(self):
        params = {"amount": 1000, "order_id": "123"}
        assert gateway.verify_signature(params, "invalid_signature") is False


@pytest.mark.asyncio
class TestTinkoffWebhook:
    @pytest.mark.asyncio
    async def test_payment_succeeded(self, mocker):
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.succeeded", "payment_id": "123"}
        result = await handle_tinkoff_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment successful"

    @pytest.mark.asyncio
    async def test_payment_canceled(self, mocker):
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.canceled", "payment_id": "123"}
        result = await handle_tinkoff_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment canceled"

    @pytest.mark.asyncio
    async def test_invalid_signature(self, mocker):
        mocker.patch.object(gateway, "verify_signature", return_value=False)
        payload = {"event": "payment.succeeded"}
        result = await handle_tinkoff_webhook(payload, "sig")
        assert result["status"] == "failed"
        assert result["message"] == "Invalid signature"
