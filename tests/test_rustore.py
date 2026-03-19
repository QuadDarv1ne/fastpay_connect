"""Тесты для RuStore Pay SDK gateway."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.payment_gateways.rustore import (
    RuStoreGateway,
    RuStorePurchaseStatus,
    RuStoreSubscriptionStatus,
    RuStoreWebhookEvent,
    gateway,
)


@pytest.fixture
def rustore_gateway():
    """Фикстура для создания экземпляра RuStore gateway."""
    with patch("app.payment_gateways.rustore.settings") as mock_settings:
        mock_settings.rustore_console_application_id = "test_app_id"
        mock_settings.rustore_api_key = "test_api_key"
        mock_settings.rustore_secret_key = "test_secret_key"
        mock_settings.rustore_return_url = "https://test.com/return"
        return RuStoreGateway()


class TestRuStoreGatewayInit:
    """Тесты инициализации RuStore gateway."""

    def test_init_with_valid_config(self, rustore_gateway):
        """Проверка инициализации с валидной конфигурацией."""
        assert rustore_gateway.console_application_id == "test_app_id"
        assert rustore_gateway.api_key == "test_api_key"
        assert rustore_gateway.secret_key == "test_secret_key"
        assert rustore_gateway.return_url == "https://test.com/return"

    def test_validate_config_success(self, rustore_gateway):
        """Проверка валидации конфигурации."""
        assert rustore_gateway.validate_config() is True


class TestRuStorePurchaseStatus:
    """Тесты статусов покупок."""

    def test_purchase_status_values(self):
        """Проверка значений статусов покупок."""
        assert RuStorePurchaseStatus.PAID.value == "PAID"
        assert RuStorePurchaseStatus.CONFIRMED.value == "CONFIRMED"
        assert RuStorePurchaseStatus.CANCELLED.value == "CANCELLED"
        assert RuStorePurchaseStatus.PROCESSING.value == "PROCESSING"

    def test_subscription_status_values(self):
        """Проверка значений статусов подписок."""
        assert RuStoreSubscriptionStatus.ACTIVE.value == "ACTIVE"
        assert RuStoreSubscriptionStatus.PAUSED.value == "PAUSED"
        assert RuStoreSubscriptionStatus.CANCELLED.value == "CANCELLED"
        assert RuStoreSubscriptionStatus.EXPIRED.value == "EXPIRED"


class TestRuStoreWebhookEvent:
    """Тесты webhook событий."""

    def test_webhook_event_values(self):
        """Проверка значений webhook событий."""
        assert RuStoreWebhookEvent.ORDER_PAID.value == "ORDER_PAID"
        assert RuStoreWebhookEvent.ORDER_CANCELLED.value == "ORDER_CANCELLED"
        assert RuStoreWebhookEvent.SUBSCRIPTION_CREATED.value == "SUBSCRIPTION_CREATED"
        assert RuStoreWebhookEvent.SUBSCRIPTION_RENEWED.value == "SUBSCRIPTION_RENEWED"


class TestVerifyWebhookSignature:
    """Тесты проверки подписи webhook."""

    def test_verify_signature_valid(self, rustore_gateway):
        """Проверка валидной подписи."""
        payload = b'{"test": "data"}'
        # Генерируем ожидаемую подпись
        import hmac
        import hashlib
        expected_sig = hmac.new(
            b"test_secret_key",
            payload,
            hashlib.sha256
        ).hexdigest()
        
        assert rustore_gateway.verify_webhook_signature(payload, expected_sig) is True

    def test_verify_signature_invalid(self, rustore_gateway):
        """Проверка невалидной подписи."""
        payload = b'{"test": "data"}'
        invalid_sig = "invalid_signature"
        
        assert rustore_gateway.verify_webhook_signature(payload, invalid_sig) is False


class TestHandleWebhook:
    """Тесты обработки webhook."""

    @pytest.mark.asyncio
    async def test_handle_webhook_order_paid(self, rustore_gateway):
        """Проверка обработки webhook ORDER_PAID."""
        payload = {
            "type": RuStoreWebhookEvent.ORDER_PAID.value,
            "order": {
                "orderId": "test_order_123",
                "status": "PAID"
            }
        }
        
        # Генерируем валидную подпись
        import hmac
        import hashlib
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(
            b"test_secret_key",
            raw_payload,
            hashlib.sha256
        ).hexdigest()
        
        result = await rustore_gateway.handle_webhook(payload, signature)
        
        assert result["processed"] is True
        assert result["event_type"] == RuStoreWebhookEvent.ORDER_PAID.value
        assert result["action"] == "fulfill_order"

    @pytest.mark.asyncio
    async def test_handle_webhook_subscription_created(self, rustore_gateway):
        """Проверка обработки webhook SUBSCRIPTION_CREATED."""
        payload = {
            "type": RuStoreWebhookEvent.SUBSCRIPTION_CREATED.value,
            "subscription": {
                "purchaseId": "test_purchase_456",
                "status": "ACTIVE"
            }
        }
        
        import hmac
        import hashlib
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()
        signature = hmac.new(
            b"test_secret_key",
            raw_payload,
            hashlib.sha256
        ).hexdigest()
        
        result = await rustore_gateway.handle_webhook(payload, signature)
        
        assert result["processed"] is True
        assert result["event_type"] == RuStoreWebhookEvent.SUBSCRIPTION_CREATED.value
        assert result["action"] == "create_subscription"

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self, rustore_gateway):
        """Проверка обработки webhook с невалидной подписью."""
        payload = {
            "type": RuStoreWebhookEvent.ORDER_PAID.value,
            "order": {"orderId": "test_order"}
        }
        
        result = await rustore_gateway.handle_webhook(payload, "invalid_signature")
        
        assert result["status"] == "failed"
        assert "Invalid signature" in result["message"]


class TestValidatePurchase:
    """Тесты валидации покупок."""

    @pytest.mark.asyncio
    async def test_validate_purchase_success(self, rustore_gateway):
        """Проверка успешной валидации покупки."""
        mock_purchase_info = {
            "status": RuStorePurchaseStatus.PAID.value,
            "purchaseId": "purchase_123",
            "amount": 100.0,
            "currency": "RUB",
            "productId": "product_123",
            "purchaseTime": 1234567890,
            "developerPayload": '{"user_id": "user_1"}'
        }
        
        with patch.object(
            rustore_gateway,
            "get_purchase_info",
            new_callable=AsyncMock,
            return_value=mock_purchase_info
        ):
            result = await rustore_gateway.validate_purchase(
                invoice_id="invoice_123",
                expected_amount=100.0
            )
            
            assert result["valid"] is True
            assert result["invoice_id"] == "invoice_123"
            assert result["amount"] == 100.0

    @pytest.mark.asyncio
    async def test_validate_purchase_amount_mismatch(self, rustore_gateway):
        """Проверка валидации с несоответствием суммы."""
        mock_purchase_info = {
            "status": RuStorePurchaseStatus.PAID.value,
            "purchaseId": "purchase_123",
            "amount": 50.0,  # Несовпадает с ожидаемой
            "currency": "RUB",
            "productId": "product_123",
        }
        
        with patch.object(
            rustore_gateway,
            "get_purchase_info",
            new_callable=AsyncMock,
            return_value=mock_purchase_info
        ):
            with pytest.raises(Exception) as exc_info:
                await rustore_gateway.validate_purchase(
                    invoice_id="invoice_123",
                    expected_amount=100.0
                )
            
            assert "Amount mismatch" in str(exc_info.value)


class TestValidateSubscription:
    """Тесты валидации подписок."""

    @pytest.mark.asyncio
    async def test_validate_subscription_active(self, rustore_gateway):
        """Проверка валидации активной подписки."""
        mock_subscription_info = {
            "status": RuStoreSubscriptionStatus.ACTIVE.value,
            "purchaseId": "purchase_456",
            "productId": "subscription_pro",
            "expirationDate": 1735689600000,
            "startTime": 1704067200000,
            "gracePeriodEnabled": True
        }
        
        with patch.object(
            rustore_gateway,
            "get_purchase_info",
            new_callable=AsyncMock,
            return_value=mock_subscription_info
        ):
            result = await rustore_gateway.validate_subscription(
                purchase_id="purchase_456"
            )
            
            assert result["valid"] is True
            assert result["status"] == RuStoreSubscriptionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_validate_subscription_expired(self, rustore_gateway):
        """Проверка валидации истёкшей подписки."""
        mock_subscription_info = {
            "status": RuStoreSubscriptionStatus.EXPIRED.value,
            "purchaseId": "purchase_456",
            "productId": "subscription_pro",
        }
        
        with patch.object(
            rustore_gateway,
            "get_purchase_info",
            new_callable=AsyncMock,
            return_value=mock_subscription_info
        ):
            result = await rustore_gateway.validate_subscription(
                purchase_id="purchase_456"
            )
            
            assert result["valid"] is False
            assert "not active" in result["reason"]


class TestModuleExports:
    """Тесты экспортируемых функций модуля."""

    def test_gateway_instance_exists(self):
        """Проверка существования глобального экземпляра gateway."""
        from app.payment_gateways import rustore
        assert hasattr(rustore, "gateway")

    def test_exported_functions(self):
        """Проверка экспортируемых функций."""
        from app.payment_gateways import rustore
        
        exported_functions = [
            "create_payment",
            "validate_purchase",
            "validate_subscription",
            "confirm_purchase",
            "cancel_purchase",
            "get_purchase_info",
            "get_products",
            "get_user_purchases",
            "get_user_subscriptions",
            "cancel_subscription",
            "verify_webhook_signature",
            "handle_rustore_webhook",
        ]
        
        for func_name in exported_functions:
            assert hasattr(rustore, func_name), f"Missing export: {func_name}"
