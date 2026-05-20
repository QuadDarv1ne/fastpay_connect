"""Интеграция с RuStore Pay SDK для серверной валидации платежей.

RuStore Pay SDK — это SDK для приёма платежей в мобильных приложениях от RuStore.
Данный модуль предоставляет серверную часть для:
- Валидации покупок через RuStore API
- Обработки webhook уведомлений о статусе платежей
- Управления подписками

Документация RuStore Pay SDK:
https://www.rustore.ru/help/sdk/pay

API Reference:
https://www.rustore.ru/help/api/
"""

import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from app.payment_gateways.base import BasePaymentGateway
from app.payment_gateways.exceptions import (
    PaymentGatewayAPIError,
    PaymentGatewayConfigError,
    PaymentGatewayError,
)
from app.settings import settings

logger = logging.getLogger(__name__)


class RuStorePurchaseType(str, Enum):
    """Типы покупок в RuStore."""

    CONSUMABLE = "CONSUMABLE"
    NON_CONSUMABLE = "NON_CONSUMABLE"
    SUBSCRIPTION = "SUBSCRIPTION"


class RuStorePurchaseStatus(str, Enum):
    """Статусы покупок в RuStore для разовых покупок."""

    INVOICE_CREATED = "INVOICE_CREATED"
    CANCELLED = "CANCELLED"
    PROCESSING = "PROCESSING"
    REJECTED = "REJECTED"
    CONFIRMED = "CONFIRMED"
    PAID = "PAID"
    REFUNDING = "REFUNDING"
    REFUNDED = "REFUNDED"
    REVERSED = "REVERSED"
    EXECUTING = "EXECUTING"


class RuStoreSubscriptionStatus(str, Enum):
    """Статусы подписок в RuStore."""

    INVOICE_CREATED = "INVOICE_CREATED"
    CANCELLED = "CANCELLED"
    PROCESSING = "PROCESSING"
    REJECTED = "REJECTED"
    PAID = "PAID"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    TERMINATED = "TERMINATED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class RuStoreWebhookEvent(str, Enum):
    """Типы webhook событий от RuStore."""

    ORDER_CREATED = "ORDER_CREATED"
    ORDER_INVOICE_CREATED = "ORDER_INVOICE_CREATED"
    ORDER_PAID = "ORDER_PAID"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_REFUNDED = "ORDER_REFUNDED"
    ORDER_REVERSED = "ORDER_REVERSED"
    SUBSCRIPTION_CREATED = "SUBSCRIPTION_CREATED"
    SUBSCRIPTION_RENEWED = "SUBSCRIPTION_RENEWED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    SUBSCRIPTION_PAUSED = "SUBSCRIPTION_PAUSED"
    SUBSCRIPTION_RESUMED = "SUBSCRIPTION_RESUMED"


class RuStoreGateway(BasePaymentGateway):
    """RuStore Pay SDK платёжный шлюз для серверной интеграции.

    RuStore Pay SDK работает на стороне Android-приложения, а серверная часть
    выполняет валидацию покупок и обрабатывает webhook уведомления.

    Основные возможности:
    - Валидация покупок по invoiceId (разовые покупки) и purchaseId (подписки)
    - Обработка webhook уведомлений о смене статуса платежа
    - Подтверждение и отмена двухстадийных платежей
    - Управление подписками

    Пример использования:
        gateway = RuStoreGateway()
        result = await gateway.validate_purchase(invoice_id="12345")
    """

    # API endpoints RuStore
    API_BASE_URL = "https://pay-api.rustore.ru"
    API_VERSION = "v2"

    def __init__(self) -> None:
        """Инициализация RuStore gateway."""
        super().__init__(
            api_key=settings.rustore_api_key,
            secret_key=settings.rustore_secret_key,
            return_url=settings.rustore_return_url,
            base_url=f"{self.API_BASE_URL}/{self.API_VERSION}",
        )
        self.console_application_id = settings.rustore_console_application_id
        self._token_cache: Optional[Dict[str, Any]] = None
        self._token_expires_at: Optional[datetime] = None

    def validate_config(self) -> bool:
        """Проверка конфигурации RuStore gateway."""
        if not self.console_application_id:
            logger.error("RuStore: console_application_id not configured")
            return False
        if not self.api_key:
            logger.error("RuStore: API key not configured")
            return False
        if not self.secret_key:
            logger.error("RuStore: secret key not configured")
            return False
        return True

    async def _get_auth_token(self) -> str:
        """Получение токена авторизации для RuStore API.

        RuStore использует OAuth2 для авторизации API запросов.
        Токен кэшируется до истечения срока действия.

        Returns:
            Строка токена авторизации

        Raises:
            PaymentGatewayConfigError: Если не удалось получить токен
        """
        # Проверяем кэш токена
        if (
            self._token_cache
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            return self._token_cache.get("access_token", "")

        if not self.validate_config():
            raise PaymentGatewayConfigError(
                "RuStore gateway not configured for authentication"
            )

        # Запрос нового токена
        auth_url = f"{self.API_BASE_URL}/auth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "client_credentials",
            "client_id": self.console_application_id,
            "client_secret": self.secret_key,
        }

        try:
            result = await self._request(
                "POST",
                auth_url,
                headers=headers,
                json_data=None,
                params=data,
            )

            self._token_cache = result
            # Устанавливаем время истечения с запасом в 5 минут
            expires_in = result.get("expires_in", 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in - 300
            )

            return result.get("access_token", "")

        except Exception as e:
            logger.error(f"Failed to get RuStore auth token: {e}")
            raise PaymentGatewayConfigError(
                f"Failed to authenticate with RuStore: {e}"
            ) from e

    async def _authenticated_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Выполнение авторизованного запроса к RuStore API.

        Args:
            method: HTTP метод (GET, POST, PUT, DELETE)
            endpoint: Endpoint API (без базового URL)
            json_data: Данные для отправки в теле запроса
            params: Query параметры

        Returns:
            Ответ от API в виде словаря
        """
        token = await self._get_auth_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return await self._request(
            method,
            url,
            headers=headers,
            json_data=json_data,
            params=params,
        )

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа в RuStore.

        Примечание: RuStore Pay SDK создаёт платежи на стороне клиента (Android).
        Данный метод используется для серверного создания заказов
        в специфических сценариях.

        Args:
            amount: Сумма платежа в рублях
            description: Описание платежа
            order_id: Уникальный идентификатор заказа

        Returns:
            Информация о созданном платеже
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("RuStore gateway not configured")

        payload = {
            "amount": amount,
            "currency": "RUB",
            "description": description[:250],
            "orderId": order_id,
            "returnUrl": self.return_url,
        }

        return await self._authenticated_request(
            "POST",
            f"/applications/{self.console_application_id}/orders",
            json_data=payload,
        )

    async def get_purchase_info(
        self,
        purchase_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Получение информации о покупке.

        Для разовых покупок используйте invoice_id.
        Для подписок используйте purchase_id.

        Args:
            purchase_id: Идентификатор покупки (для подписок)
            invoice_id: Идентификатор счёта (для разовых покупок)

        Returns:
            Информация о покупке
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("RuStore gateway not configured")

        if invoice_id:
            # Получение информации о разовой покупке
            return await self._authenticated_request(
                "GET",
                f"/applications/{self.console_application_id}/invoices/{invoice_id}",
            )
        elif purchase_id:
            # Получение информации о подписке
            return await self._authenticated_request(
                "GET",
                f"/applications/{self.console_application_id}/subscriptions/{purchase_id}",
            )
        else:
            raise PaymentGatewayError(
                "Either purchase_id or invoice_id must be provided"
            )

    async def validate_purchase(
        self,
        invoice_id: str,
        expected_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Валидация покупки на сервере.

        Рекомендуется вызывать данный метод после успешной оплаты
        на стороне клиента для подтверждения подлинности транзакции.

        Args:
            invoice_id: Идентификатор счёта из SDK
            expected_amount: Ожидаемая сумма для проверки (опционально)

        Returns:
            Результат валидации с информацией о покупке

        Raises:
            PaymentGatewayError: Если валидация не прошла
        """
        purchase_info = await self.get_purchase_info(invoice_id=invoice_id)

        # Проверяем статус покупки
        status = purchase_info.get("status", "")
        if status not in (
            RuStorePurchaseStatus.PAID.value,
            RuStorePurchaseStatus.CONFIRMED.value,
        ):
            raise PaymentGatewayError(
                f"Purchase not completed. Status: {status}",
                details=purchase_info,
            )

        # Проверяем сумму если указана
        if expected_amount is not None:
            actual_amount = purchase_info.get("amount", 0)
            if abs(actual_amount - expected_amount) > 0.01:
                raise PaymentGatewayError(
                    f"Amount mismatch. Expected: {expected_amount}, Actual: {actual_amount}",
                    details=purchase_info,
                )

        return {
            "valid": True,
            "purchase_id": purchase_info.get("purchaseId"),
            "invoice_id": invoice_id,
            "status": status,
            "amount": purchase_info.get("amount"),
            "currency": purchase_info.get("currency", "RUB"),
            "product_id": purchase_info.get("productId"),
            "purchase_time": purchase_info.get("purchaseTime"),
            "developer_payload": purchase_info.get("developerPayload"),
        }

    async def validate_subscription(
        self,
        purchase_id: str,
    ) -> Dict[str, Any]:
        """Валидация подписки на сервере.

        Args:
            purchase_id: Идентификатор покупки подписки

        Returns:
            Результат валидации с информацией о подписке
        """
        subscription_info = await self.get_purchase_info(purchase_id=purchase_id)

        status = subscription_info.get("status", "")
        if status != RuStoreSubscriptionStatus.ACTIVE.value:
            return {
                "valid": False,
                "status": status,
                "reason": f"Subscription is not active: {status}",
                "subscription_info": subscription_info,
            }

        return {
            "valid": True,
            "purchase_id": purchase_id,
            "status": status,
            "product_id": subscription_info.get("productId"),
            "expiration_date": subscription_info.get("expirationDate"),
            "start_time": subscription_info.get("startTime"),
            "grace_period_enabled": subscription_info.get("gracePeriodEnabled", False),
        }

    async def confirm_purchase(self, invoice_id: str) -> Dict[str, Any]:
        """Подтверждение двухстадийной покупки.

        Используется для подтверждения холдированных средств
        при двухстадийной оплате.

        Args:
            invoice_id: Идентификатор счёта

        Returns:
            Результат подтверждения
        """
        return await self._authenticated_request(
            "POST",
            f"/applications/{self.console_application_id}/invoices/{invoice_id}/confirm",
        )

    async def cancel_purchase(self, invoice_id: str) -> Dict[str, Any]:
        """Отмена двухстадийной покупки.

        Используется для отмены холдированных средств
        при двухстадийной оплате.

        Args:
            invoice_id: Идентификатор счёта

        Returns:
            Результат отмены
        """
        return await self._authenticated_request(
            "POST",
            f"/applications/{self.console_application_id}/invoices/{invoice_id}/cancel",
        )

    async def get_products(
        self,
        product_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Получение списка продуктов из RuStore.

        Args:
            product_ids: Список идентификаторов продуктов (опционально)

        Returns:
            Список продуктов с информацией о ценах
        """
        params = {}
        if product_ids:
            params["productIds"] = ",".join(product_ids)

        return await self._authenticated_request(
            "GET",
            f"/applications/{self.console_application_id}/products",
            params=params if params else None,
        )

    async def get_user_purchases(self, user_id: str) -> Dict[str, Any]:
        """Получение списка покупок пользователя.

        Args:
            user_id: Идентификатор пользователя (appUserId из SDK)

        Returns:
            Список покупок пользователя
        """
        return await self._authenticated_request(
            "GET",
            f"/applications/{self.console_application_id}/users/{user_id}/purchases",
        )

    async def get_user_subscriptions(self, user_id: str) -> Dict[str, Any]:
        """Получение списка подписок пользователя.

        Args:
            user_id: Идентификатор пользователя (appUserId из SDK)

        Returns:
            Список подписок пользователя
        """
        return await self._authenticated_request(
            "GET",
            f"/applications/{self.console_application_id}/users/{user_id}/subscriptions",
        )

    async def cancel_subscription(
        self,
        purchase_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Отмена подписки.

        Args:
            purchase_id: Идентификатор покупки подписки
            reason: Причина отмены (опционально)

        Returns:
            Результат отмены
        """
        payload = {}
        if reason:
            payload["reason"] = reason

        return await self._authenticated_request(
            "POST",
            f"/applications/{self.console_application_id}/subscriptions/{purchase_id}/cancel",
            json_data=payload if payload else None,
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Проверка подписи webhook уведомления.

        RuStore отправляет webhook с подписью в заголовке X-Signature.

        Args:
            payload: Сырые данные webhook (bytes)
            signature: Подпись из заголовка X-Signature

        Returns:
            True если подпись валидна
        """
        if not self.secret_key:
            logger.warning("RuStore: secret key not configured, skipping signature verification")
            return True

        expected_signature = hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
    ) -> Dict[str, str]:
        """Обработка webhook уведомления от RuStore.

        RuStore отправляет webhook при изменении статуса заказа или подписки.

        Args:
            payload: Данные webhook уведомления
            signature: Подпись из заголовка X-Signature

        Returns:
            Результат обработки webhook
        """
        # Проверяем подпись
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()
        if not self.verify_webhook_signature(raw_payload, signature):
            logger.warning("Invalid RuStore webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event_type = payload.get("type", "")
        logger.info(f"Processing RuStore webhook event: {event_type}")

        # Извлекаем данные заказа/подписки
        order_data = payload.get("order", payload.get("subscription", {}))
        order_id = order_data.get("orderId") or order_data.get("purchaseId")
        status = order_data.get("status", "")

        result = {
            "event_type": event_type,
            "order_id": order_id,
            "status": status,
            "processed": True,
        }

        # Обработка различных типов событий
        if event_type in (
            RuStoreWebhookEvent.ORDER_PAID.value,
            RuStoreWebhookEvent.ORDER_CONFIRMED.value,
        ):
            result["message"] = "Payment successful"
            result["action"] = "fulfill_order"

        elif event_type == RuStoreWebhookEvent.ORDER_CANCELLED.value:
            result["message"] = "Payment cancelled"
            result["action"] = "cancel_order"

        elif event_type == RuStoreWebhookEvent.ORDER_REFUNDED.value:
            result["message"] = "Payment refunded"
            result["action"] = "process_refund"

        elif event_type == RuStoreWebhookEvent.SUBSCRIPTION_CREATED.value:
            result["message"] = "Subscription created"
            result["action"] = "create_subscription"

        elif event_type == RuStoreWebhookEvent.SUBSCRIPTION_RENEWED.value:
            result["message"] = "Subscription renewed"
            result["action"] = "renew_subscription"

        elif event_type == RuStoreWebhookEvent.SUBSCRIPTION_CANCELLED.value:
            result["message"] = "Subscription cancelled"
            result["action"] = "cancel_subscription"

        elif event_type == RuStoreWebhookEvent.SUBSCRIPTION_EXPIRED.value:
            result["message"] = "Subscription expired"
            result["action"] = "expire_subscription"

        else:
            logger.info(f"Unhandled RuStore webhook event: {event_type}")
            result["message"] = f"Event {event_type} acknowledged"
            result["action"] = "acknowledge"

        return result


# Глобальный экземпляр gateway
gateway = RuStoreGateway()

# Экспортируемые функции
create_payment = gateway.create_payment
validate_purchase = gateway.validate_purchase
validate_subscription = gateway.validate_subscription
confirm_purchase = gateway.confirm_purchase
cancel_purchase = gateway.cancel_purchase
get_purchase_info = gateway.get_purchase_info
get_products = gateway.get_products
get_user_purchases = gateway.get_user_purchases
get_user_subscriptions = gateway.get_user_subscriptions
cancel_subscription = gateway.cancel_subscription
verify_webhook_signature = gateway.verify_webhook_signature
handle_rustore_webhook = gateway.handle_webhook
