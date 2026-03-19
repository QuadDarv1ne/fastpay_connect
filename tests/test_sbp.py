"""
Tests for SBP (Система Быстрых Платежей) gateway.
"""

import json
import pytest
import hashlib
import hmac
import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.payment_gateways.sbp import (
    SBPGateway,
    SBPStatus,
    SBPBank,
    gateway,
)
from app.payment_gateways.exceptions import (
    PaymentGatewayConfigError,
    PaymentGatewayError,
)


@pytest.fixture
def sbp_gateway():
    """Фикстура для создания экземпляра SBP gateway."""
    with patch("app.payment_gateways.sbp.settings") as mock_settings:
        mock_settings.sbp_api_key = "test_api_key"
        mock_settings.sbp_secret_key = "test_secret_key"
        mock_settings.sbp_merchant_id = "test_merchant_id"
        mock_settings.sbp_return_url = "https://test.com/return"
        return SBPGateway()


class TestSBPBank:
    """Тесты справочника банков СБП."""

    def test_get_bic_sberbank(self):
        """Проверка получения BIC Сбербанка."""
        bic = SBPBank.get_bic("sberbank")
        assert bic == "044525225"

    def test_get_bic_tinkoff(self):
        """Проверка получения BIC Тинькофф."""
        bic = SBPBank.get_bic("tinkoff")
        assert bic == "044525974"

    def test_get_bic_invalid(self):
        """Проверка получения BIC несуществующего банка."""
        bic = SBPBank.get_bic("invalid_bank")
        assert bic is None

    def test_get_all_banks(self):
        """Проверка получения списка всех банков."""
        banks = SBPBank.get_all_banks()
        assert len(banks) > 0
        assert all("code" in bank for bank in banks)
        assert all("name" in bank for bank in banks)
        assert all("bic" in bank for bank in banks)

    def test_get_bic_case_insensitive(self):
        """Проверка регистронезависимости кода банка."""
        assert SBPBank.get_bic("SBERBANK") == SBPBank.get_bic("sberbank")


class TestSBPStatus:
    """Тесты статусов СБП."""

    def test_status_values(self):
        """Проверка значений статусов."""
        assert SBPStatus.PENDING.value == "PENDING"
        assert SBPStatus.PAID.value == "PAID"
        assert SBPStatus.REJECTED.value == "REJECTED"
        assert SBPStatus.EXPIRED.value == "EXPIRED"
        assert SBPStatus.REFUNDED.value == "REFUNDED"


class TestSBPGatewayInit:
    """Тесты инициализации SBP gateway."""

    def test_init_with_valid_config(self, sbp_gateway):
        """Проверка инициализации с валидной конфигурацией."""
        assert sbp_gateway.merchant_id == "test_merchant_id"
        assert sbp_gateway.api_key == "test_api_key"
        assert sbp_gateway.secret_key == "test_secret_key"

    def test_validate_config_success(self, sbp_gateway):
        """Проверка валидации конфигурации."""
        assert sbp_gateway.validate_config() is True

    def test_validate_config_no_merchant_id(self):
        """Проверка валидации без merchant_id."""
        with patch("app.payment_gateways.sbp.settings") as mock_settings:
            mock_settings.sbp_api_key = "test_api_key"
            mock_settings.sbp_secret_key = "test_secret_key"
            mock_settings.sbp_merchant_id = None

            gw = SBPGateway()
            assert gw.validate_config() is False

    def test_validate_config_no_api_key(self):
        """Проверка валидации без API key."""
        with patch("app.payment_gateways.sbp.settings") as mock_settings:
            mock_settings.sbp_api_key = None
            mock_settings.sbp_secret_key = "test_secret_key"
            mock_settings.sbp_merchant_id = "test_merchant_id"

            gw = SBPGateway()
            assert gw.validate_config() is False


class TestSBPSignature:
    """Тесты подписи запросов СБП."""

    def test_generate_signature(self, sbp_gateway):
        """Проверка генерации подписи."""
        method = "POST"
        path = "/payments"
        timestamp = "2024-01-01T00:00:00.000Z"
        body = '{"amount":1000}'

        signature = sbp_gateway.generate_signature(method, path, timestamp, body)

        assert signature is not None
        assert len(signature) > 0
        # Проверка что это base64
        base64.b64decode(signature)


class TestVerifyWebhookSignature:
    """Тесты проверки подписи webhook."""

    def test_verify_signature_valid(self, sbp_gateway):
        """Проверка валидной подписи webhook."""
        payload = {"event": "payment.paid", "payment": {"id": "123"}}
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()

        # Генерируем правильную подпись
        body_hash = hashlib.sha256(raw_payload).hexdigest().lower()
        signature_str = f"POST:/webhooks:{timestamp}:{body_hash}"
        expected_signature = hmac.new(
            b"test_secret_key",
            signature_str.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(expected_signature).decode()

        assert sbp_gateway.verify_webhook_signature(raw_payload, signature_b64, timestamp) is True

    def test_verify_signature_invalid(self, sbp_gateway):
        """Проверка невалидной подписи webhook."""
        payload = {"event": "payment.paid"}
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()

        assert sbp_gateway.verify_webhook_signature(
            raw_payload, "invalid_signature", timestamp
        ) is False

    def test_verify_signature_expired_timestamp(self, sbp_gateway):
        """Проверка webhook с истёкшим timestamp."""
        payload = {"event": "payment.paid"}
        # Timestamp 10 минут назад
        from datetime import timedelta
        old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        timestamp = old_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()

        # Генерируем правильную подпись но для старого timestamp
        body_hash = hashlib.sha256(raw_payload).hexdigest().lower()
        signature_str = f"POST:/webhooks:{timestamp}:{body_hash}"
        expected_signature = hmac.new(
            b"test_secret_key",
            signature_str.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(expected_signature).decode()

        assert sbp_gateway.verify_webhook_signature(
            raw_payload, signature_b64, timestamp
        ) is False


class TestHandleWebhook:
    """Тесты обработки webhook."""

    @pytest.mark.asyncio
    async def test_handle_webhook_payment_paid(self, sbp_gateway):
        """Проверка обработки webhook payment.paid."""
        payload = {
            "event": "payment.paid",
            "payment": {
                "id": "payment_123",
                "status": "PAID",
            },
        }
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()

        # Генерируем правильную подпись
        body_hash = hashlib.sha256(raw_payload).hexdigest().lower()
        signature_str = f"POST:/webhooks:{timestamp}:{body_hash}"
        expected_signature = hmac.new(
            b"test_secret_key",
            signature_str.encode(),
            hashlib.sha256,
        ).digest()
        signature_b64 = base64.b64encode(expected_signature).decode()

        result = await sbp_gateway.handle_webhook(payload, signature_b64, timestamp)

        assert result["processed"] is True
        assert result["event_type"] == "payment.paid"
        assert result["action"] == "fulfill_order"

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self, sbp_gateway):
        """Проверка обработки webhook с невалидной подписью."""
        payload = {"event": "payment.paid", "payment": {"id": "123"}}
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        result = await sbp_gateway.handle_webhook(payload, "invalid", timestamp)

        assert result["status"] == "failed"
        assert "Invalid signature" in result["message"]


class TestCreatePayment:
    """Тесты создания платежа."""

    @pytest.mark.asyncio
    async def test_create_payment_success(self, sbp_gateway):
        """Проверка успешного создания платежа."""
        mock_response = {
            "id": "payment_123",
            "status": "PENDING",
            "paymentUrl": "https://sbp.nspk.ru/pay/123",
            "qrCode": "base64_qr_code",
            "expiresAt": "2024-01-01T01:00:00Z",
            "createdAt": "2024-01-01T00:30:00Z",
        }

        with patch.object(
            sbp_gateway, "_authenticated_request", new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await sbp_gateway.create_payment(
                amount=1000.0,
                order_id="order_123",
                description="Test payment",
                phone="+79991234567",
            )

            assert result["payment_id"] == "payment_123"
            assert result["order_id"] == "order_123"
            assert result["amount"] == 1000.0
            assert result["payment_url"] == "https://sbp.nspk.ru/pay/123"
            assert result["qr_code"] == "base64_qr_code"

    @pytest.mark.asyncio
    async def test_create_payment_invalid_amount(self, sbp_gateway):
        """Проверка создания платежа с некорректной суммой."""
        with pytest.raises(PaymentGatewayError, match="Amount must be positive"):
            await sbp_gateway.create_payment(
                amount=-100.0,
                order_id="order_123",
                description="Test payment",
            )

    @pytest.mark.asyncio
    async def test_create_payment_phone_normalization(self, sbp_gateway):
        """Проверка нормализации номера телефона."""
        mock_response = {"id": "payment_123", "status": "PENDING"}

        with patch.object(
            sbp_gateway, "_authenticated_request", new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_request:
            await sbp_gateway.create_payment(
                amount=1000.0,
                order_id="order_123",
                description="Test payment",
                phone="89991234567",  # Номер с 8
            )

            # Проверяем что номер был нормализован
            call_args = mock_request.call_args
            payload = call_args[1]["json_data"]
            assert payload["phone"] == "+79991234567"


class TestRefundPayment:
    """Тесты возврата платежа."""

    @pytest.mark.asyncio
    async def test_refund_payment_success(self, sbp_gateway):
        """Проверка успешного возврата."""
        mock_response = {
            "id": "refund_123",
            "status": "REFUNDED",
            "amount": 1000.0,
            "reason": "Customer request",
            "createdAt": "2024-01-01T02:00:00Z",
        }

        with patch.object(
            sbp_gateway, "_authenticated_request", new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await sbp_gateway.refund_payment(
                payment_id="payment_123",
                amount=1000.0,
                reason="Customer request",
            )

            assert result["refund_id"] == "refund_123"
            assert result["payment_id"] == "payment_123"
            assert result["amount"] == 1000.0


class TestCancelPayment:
    """Тесты отмены платежа."""

    @pytest.mark.asyncio
    async def test_cancel_payment_success(self, sbp_gateway):
        """Проверка успешной отмены."""
        mock_response = {
            "status": "REJECTED",
            "cancelledAt": "2024-01-01T02:00:00Z",
        }

        with patch.object(
            sbp_gateway, "_authenticated_request", new_callable=AsyncMock,
            return_value=mock_response
        ):
            result = await sbp_gateway.cancel_payment(payment_id="payment_123")

            assert result["payment_id"] == "payment_123"
            assert result["status"] == "REJECTED"


class TestModuleExports:
    """Тесты экспортируемых функций модуля."""

    def test_gateway_instance_exists(self):
        """Проверка существования глобального экземпляра gateway."""
        from app.payment_gateways import sbp
        assert hasattr(sbp, "gateway")

    def test_exported_functions(self):
        """Проверка экспортируемых функций."""
        from app.payment_gateways import sbp

        exported_functions = [
            "create_payment",
            "get_payment_info",
            "get_payment_by_order_id",
            "refund_payment",
            "cancel_payment",
            "verify_webhook_signature",
            "handle_sbp_webhook",
            "get_all_banks",
            "get_bank_bic",
        ]

        for func_name in exported_functions:
            assert hasattr(sbp, func_name), f"Missing export: {func_name}"
