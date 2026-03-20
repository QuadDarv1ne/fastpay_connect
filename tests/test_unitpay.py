"""Tests for UnitPay payment gateway."""

import pytest
from app.payment_gateways.unitpay import gateway, handle_unitpay_webhook


class TestUnitPaySignature:
    """Тесты подписи UnitPay."""

    def test_generate_signature(self):
        """Тест генерации подписи."""
        params = {"amount": 1000, "order_id": "123"}
        result = gateway.generate_signature(params)
        assert isinstance(result, str)
        assert len(result) == 64

    def test_verify_signature_valid(self):
        """Тест проверки валидной подписи."""
        params = {"amount": 1000, "order_id": "123"}
        signature = gateway.generate_signature(params)
        assert gateway.verify_signature(params, signature) is True

    def test_verify_signature_invalid(self):
        """Тест проверки невалидной подписи."""
        params = {"amount": 1000, "order_id": "123"}
        assert gateway.verify_signature(params, "invalid_signature") is False

    def test_generate_signature_consistency(self):
        """Тест консистентности генерации подписи."""
        params = {"amount": 1000, "order_id": "123"}
        sig1 = gateway.generate_signature(params)
        sig2 = gateway.generate_signature(params)
        assert sig1 == sig2

    def test_generate_signature_different_params(self):
        """Тест генерации подписи с разными параметрами."""
        params1 = {"amount": 1000, "order_id": "123"}
        params2 = {"amount": 2000, "order_id": "123"}
        sig1 = gateway.generate_signature(params1)
        sig2 = gateway.generate_signature(params2)
        assert sig1 != sig2

    def test_generate_signature_with_different_data_types(self):
        """Тест генерации подписи с разными типами данных."""
        params_int = {"amount": 1000, "order_id": "123"}
        params_float = {"amount": 1000.50, "order_id": "123"}
        sig_int = gateway.generate_signature(params_int)
        sig_float = gateway.generate_signature(params_float)
        assert sig_int != sig_float


@pytest.mark.asyncio
class TestUnitPayWebhook:
    """Тесты webhook UnitPay."""

    @pytest.mark.asyncio
    async def test_payment_succeeded(self, mocker):
        """Тест успешного платежа."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.succeeded", "payment_id": "123"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment successful"

    @pytest.mark.asyncio
    async def test_payment_canceled(self, mocker):
        """Тест отмены платежа."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.canceled", "payment_id": "123"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment canceled"

    @pytest.mark.asyncio
    async def test_payment_refunded(self, mocker):
        """Тест возврата платежа."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.refunded", "payment_id": "123"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment refunded"

    @pytest.mark.asyncio
    async def test_invalid_signature(self, mocker):
        """Тест невалидной подписи."""
        mocker.patch.object(gateway, "verify_signature", return_value=False)
        payload = {"event": "payment.succeeded"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "failed"
        assert result["message"] == "Invalid signature"

    @pytest.mark.asyncio
    async def test_unknown_event(self, mocker):
        """Тест неизвестного события."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.unknown", "payment_id": "123"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "ignored"
        assert result["message"] == "Event not recognized"

    @pytest.mark.asyncio
    async def test_missing_event(self, mocker):
        """Тест отсутствия события."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"payment_id": "123"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "ignored"
        assert result["message"] == "Event not recognized"

    @pytest.mark.asyncio
    async def test_missing_payment_id(self, mocker):
        """Тест отсутствия payment_id."""
        mocker.patch.object(gateway, "verify_signature", return_value=True)
        payload = {"event": "payment.succeeded"}
        result = await handle_unitpay_webhook(payload, "sig")
        assert result["status"] == "processed"
        assert result["message"] == "Payment successful"


@pytest.mark.asyncio
class TestUnitPayCreatePayment:
    """Тесты создания платежа UnitPay."""

    @pytest.mark.asyncio
    async def test_create_payment_payload(self, mocker):
        """Тест формирования payload для платежа."""
        mock_request = mocker.patch.object(
            gateway, "_request", return_value={"status": "success"}
        )
        
        await gateway.create_payment(
            amount=1000.0,
            description="Test payment",
            order_id="order_123"
        )
        
        assert mock_request.called
        call_args = mock_request.call_args
        assert call_args[0][0] == "POST"
        assert "payment" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_payment_amount(self, mocker):
        """Тест суммы платежа."""
        mock_request = mocker.patch.object(
            gateway, "_request", return_value={"status": "success"}
        )
        
        await gateway.create_payment(
            amount=2500.50,
            description="Test payment",
            order_id="order_123"
        )
        
        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json_data"]
        assert payload["amount"] == 2500.50

    @pytest.mark.asyncio
    async def test_create_payment_description_truncated(self, mocker):
        """Тест обрезки описания платежа."""
        mock_request = mocker.patch.object(
            gateway, "_request", return_value={"status": "success"}
        )
        
        long_description = "A" * 300
        await gateway.create_payment(
            amount=1000.0,
            description=long_description,
            order_id="order_123"
        )
        
        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json_data"]
        assert len(payload["description"]) <= 250

    @pytest.mark.asyncio
    async def test_create_payment_currency(self, mocker):
        """Тест валюты платежа."""
        mock_request = mocker.patch.object(
            gateway, "_request", return_value={"status": "success"}
        )
        
        await gateway.create_payment(
            amount=1000.0,
            description="Test payment",
            order_id="order_123"
        )
        
        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json_data"]
        assert payload["currency"] == "RUB"

    @pytest.mark.asyncio
    async def test_create_payment_order_id(self, mocker):
        """Тест order_id платежа."""
        mock_request = mocker.patch.object(
            gateway, "_request", return_value={"status": "success"}
        )
        
        await gateway.create_payment(
            amount=1000.0,
            description="Test payment",
            order_id="custom_order_456"
        )
        
        call_kwargs = mock_request.call_args[1]
        payload = call_kwargs["json_data"]
        assert payload["order_id"] == "custom_order_456"
