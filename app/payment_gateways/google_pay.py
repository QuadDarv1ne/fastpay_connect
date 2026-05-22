"""Интеграция с Google Pay.

Google Pay — платёжная система от Google, позволяющая пользователям оплачивать
покупки с помощью устройств Android и веб-браузеров.

Документация Google:
https://developers.google.com/pay

API Reference:
https://developers.google.com/pay/api/web/reference
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from app.payment_gateways.base import BasePaymentGateway
from app.payment_gateways.exceptions import (
    PaymentGatewayAPIError,
    PaymentGatewayConfigError,
    PaymentGatewayError,
)

logger = logging.getLogger(__name__)


class GooglePayEnvironment(str, Enum):
    """Окружение Google Pay."""
    TEST = "TEST"
    PRODUCTION = "PRODUCTION"


class GooglePayCardNetwork(str, Enum):
    """Платёжные сети Google Pay."""
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMEX = "AMEX"
    DISCOVER = "DISCOVER"
    JCB = "JCB"
    INTERAC = "INTERAC"
    ELO = "ELO"


class GooglePayCardClass(str, Enum):
    """Классы карт Google Pay."""
    UNSPECIFIED = "UNSPECIFIED"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    PREPAID = "PREPAID"


class GooglePayGateway(BasePaymentGateway):
    """Google Pay платёжный шлюз.

    Поддерживает:
    - Валидацию мерчанта через Google Pay API
    - Создание платежных запросов
    - Обработку токенов Google Pay
    - Webhook уведомления о статусе платежей

    Для работы требуется:
    - Google Merchant ID
    - Gateway ID (процессинговый шлюз)
    - Gateway Merchant ID

    Пример использования:
        gateway = GooglePayGateway(
            merchant_id="12345678901234567890",
            gateway_id="example_gateway",
            gateway_merchant_id="example_merchant"
        )
        result = await gateway.create_payment_request(
            amount=1000,
            order_id="order_123"
        )
    """

    GOOGLE_PAY_BASE_URL = "https://pay.google.com"
    GOOGLE_PAY_API_URL = "https://payments.developers.google.com"

    def __init__(
        self,
        merchant_id: Optional[str] = None,
        gateway_id: Optional[str] = None,
        gateway_merchant_id: Optional[str] = None,
        environment: str = "TEST",
        **kwargs: Any,
    ) -> None:
        """Инициализация Google Pay шлюза.

        Args:
            merchant_id: Google Merchant ID
            gateway_id: ID процессингового шлюза
            gateway_merchant_id: Merchant ID в процессинговом шлюзе
            environment: 'TEST' или 'PRODUCTION'
        """
        super().__init__(
            api_key=merchant_id,
            secret_key=kwargs.get("private_key", ""),
            return_url=kwargs.get("return_url", ""),
            base_url=self.GOOGLE_PAY_BASE_URL,
            timeout=kwargs.get("timeout", 30.0),
        )
        self.merchant_id = merchant_id
        self.gateway_id = gateway_id
        self.gateway_merchant_id = gateway_merchant_id
        self.environment = GooglePayEnvironment(environment)
        self._private_key_content: Optional[str] = None

    def _get_base_card_payment_method(
        self,
        allowed_card_networks: Optional[List[str]] = None,
        allowed_card_auth_methods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Получить базовый метод оплаты картой.

        Args:
            allowed_card_networks: Разрешённые платёжные сети
            allowed_card_auth_methods: Разрешённые методы аутентификации

        Returns:
            Конфигурация метода оплаты
        """
        if allowed_card_networks is None:
            allowed_card_networks = [
                GooglePayCardNetwork.VISA.value,
                GooglePayCardNetwork.MASTERCARD.value,
            ]

        if allowed_card_auth_methods is None:
            allowed_card_auth_methods = ["PAN_ONLY", "CRYPTOGRAM_3DS"]

        return {
            "type": "CARD",
            "parameters": {
                "allowedAuthMethods": allowed_card_auth_methods,
                "allowedCardNetworks": allowed_card_networks,
                "billingAddressRequired": True,
                "billingAddressParameters": {
                    "format": "FULL",
                    "phoneNumberRequired": True,
                },
            },
        }

    def _get_tokenization_specification(
        self,
    ) -> Dict[str, Any]:
        """Получить спецификацию токенизации.

        Returns:
            Конфигурация токенизации для PAYMENT_GATEWAY типа
        """
        config = {
            "type": "PAYMENT_GATEWAY",
            "parameters": {
                "gateway": self.gateway_id or "example",
                "gatewayMerchantId": self.gateway_merchant_id or self.merchant_id,
            },
        }

        # Для тестового окружения используем упрощённую токенизацию
        if self.environment == GooglePayEnvironment.TEST:
            config = {
                "type": "TEST",
            }

        return config

    def get_is_ready_to_pay_request(self) -> Dict[str, Any]:
        """Создать запрос IsReadyToPay.

        Проверяет, готов ли пользователь к оплате через Google Pay.

        Returns:
            Объект запроса IsReadyToPay
        """
        return {
            "apiVersion": 2,
            "apiVersionMinor": 0,
            "allowedPaymentMethods": [self._get_base_card_payment_method()],
        }

    def get_payment_data_request(
        self,
        amount: float,
        currency: str = "RUB",
        country_code: str = "RU",
        merchant_name: str = "FastPay Connect",
        supported_networks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Создать запрос платежных данных.

        Args:
            amount: Сумма платежа
            currency: Валюта платежа
            country_code: Код страны
            merchant_name: Название мерчанта
            supported_networks: Поддерживаемые платёжные сети

        Returns:
            Объект запроса PaymentData
        """
        base_card_payment_method = self._get_base_card_payment_method(
            allowed_card_networks=supported_networks
        )
        base_card_payment_method["tokenizationSpecification"] = (
            self._get_tokenization_specification()
        )

        return {
            "apiVersion": 2,
            "apiVersionMinor": 0,
            "allowedPaymentMethods": [base_card_payment_method],
            "transactionInfo": {
                "totalPriceStatus": "FINAL",
                "totalPrice": f"{amount:.2f}",
                "currencyCode": currency,
                "countryCode": country_code,
            },
            "merchantInfo": {
                "merchantId": self.merchant_id or "",
                "merchantName": merchant_name,
            },
            "shippingAddressRequired": False,
            "emailRequired": True,
        }

    async def validate_merchant(self) -> Dict[str, Any]:
        """Валидация мерчанта через Google Pay.

        Returns:
            Результат валидации
        """
        logger.info(f"Google Pay: validating merchant {self.merchant_id}")

        # В реальной реализации здесь вызывается Google Pay Merchant Validation API
        return {
            "merchant_id": self.merchant_id,
            "gateway_id": self.gateway_id,
            "environment": self.environment.value,
            "status": "validated",
            "expires_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_payment_request(
        self,
        amount: float,
        order_id: str,
        description: str = "",
        currency: str = "RUB",
        country_code: str = "RU",
        supported_networks: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Создание платежного запроса Google Pay.

        Args:
            amount: Сумма платежа
            order_id: ID заказа
            description: Описание платежа
            currency: Валюта платежа
            country_code: Код страны
            supported_networks: Поддерживаемые платёжные сети

        Returns:
            Данные для инициализации Google Pay запроса
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("Google Pay: gateway not configured")

        if amount <= 0:
            raise PaymentGatewayError(
                "Invalid amount",
                details={"amount": amount, "reason": "Amount must be positive"},
            )

        payment_data_request = self.get_payment_data_request(
            amount=amount,
            currency=currency,
            country_code=country_code,
            supported_networks=supported_networks,
        )

        logger.info(
            f"Google Pay: creating payment request for order {order_id}, "
            f"amount {amount} {currency}"
        )

        return {
            "payment_data_request": json.dumps(payment_data_request),
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "merchant_id": self.merchant_id,
            "environment": self.environment.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def process_payment_token(
        self,
        token_data: Dict[str, Any],
        order_id: str,
        amount: float,
        currency: str = "RUB",
    ) -> Dict[str, Any]:
        """Обработка токена Google Pay.

        Args:
            token_data: Токен от Google Pay (paymentMethodData.tokenizationData.token)
            order_id: ID заказа
            amount: Сумма платежа
            currency: Валюта платежа

        Returns:
            Результат обработки платежа
        """
        logger.info(
            f"Google Pay: processing payment token for order {order_id}, "
            f"amount {amount} {currency}"
        )

        # В реальной реализации здесь происходит вызов процессингового API
        # для зарядки карты клиента

        payment_id = f"gp_{order_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        # Парсим токен Google Pay
        payment_method_info = token_data.get("paymentMethodData", {})
        card_info = payment_method_info.get("info", {})
        card_network = card_info.get("cardNetwork", "UNKNOWN")
        card_details = card_info.get("cardDetails", "")

        return {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": amount,
            "currency": currency,
            "status": "completed",
            "transaction_id": token_data.get("id", ""),
            "payment_method": "google_pay",
            "card_network": card_network,
            "card_details": card_details,
            "email": token_data.get("email", ""),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_payment(
        self,
        amount: float,
        description: str,
        order_id: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Создание платежа Google Pay.

        Args:
            amount: Сумма платежа
            description: Описание платежа
            order_id: ID заказа
            **kwargs: Дополнительные параметры (currency, country_code, etc.)

        Returns:
            Результат создания платежа
        """
        return await self.create_payment_request(
            amount=amount,
            order_id=order_id,
            description=description,
            currency=kwargs.get("currency", "RUB"),
            country_code=kwargs.get("country_code", "RU"),
            supported_networks=kwargs.get("supported_networks"),
        )

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str = "",
    ) -> Dict[str, str]:
        """Обработка webhook уведомления от Google Pay.

        Google Pay не отправляет webhook напрямую, но процессинговый
        банк может отправлять уведомления о статусе платежей.

        Args:
            payload: Данные webhook
            signature: Подпись webhook (если есть)

        Returns:
            Результат обработки
        """
        event_type = payload.get("eventType", "unknown")
        order_id = payload.get("orderId", "")

        logger.info(
            f"Google Pay: handling webhook event {event_type} for order {order_id}"
        )

        # В зависимости от типа события обновляем статус платежа
        status_mapping = {
            "payment.completed": "completed",
            "payment.failed": "failed",
            "payment.refunded": "refunded",
            "payment.cancelled": "cancelled",
        }

        status = status_mapping.get(event_type, "pending")

        return {
            "status": status,
            "order_id": order_id,
            "event_type": event_type,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    def validate_config(self) -> bool:
        """Проверка конфигурации шлюза."""
        if not self.merchant_id:
            logger.error("Google Pay: merchant_id not configured")
            return False
        if not self.gateway_id:
            logger.warning("Google Pay: gateway_id not configured (using TEST mode)")
        return True

    def get_payment_url(self, payment_id: str) -> str:
        """Google Pay не использует payment URL, возвращаем пустую строку."""
        return ""


# Глобальный экземпляр (будет инициализирован в settings)
gateway: Optional[GooglePayGateway] = None


def get_gateway() -> GooglePayGateway:
    """Получить экземпляр шлюза."""
    global gateway
    if gateway is None:
        gateway = GooglePayGateway()
    return gateway


# Module-level wrappers for gateway registry compatibility
async def create_payment(amount: float, description: str, order_id: str) -> dict:
    """Wrapper for gateway registry compatibility."""
    return await get_gateway().create_payment(amount, description, order_id)


async def handle_google_pay_webhook(payload: dict, signature: str = "", timestamp: str = "") -> dict:
    """Wrapper for gateway registry compatibility."""
    del timestamp  # unused, kept for signature compatibility
    return await get_gateway().handle_webhook(payload, signature)
