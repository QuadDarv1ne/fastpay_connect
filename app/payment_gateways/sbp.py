"""Интеграция с Системой Быстрых Платежей (СБП).

СБП — российская система платежей, позволяющая переводить деньги
по номеру телефона через СБП.

Документация НСПК:
https://sbp.nspk.ru/

API Reference:
https://sbp.nspk.ru/api
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
from app.settings import settings

logger = logging.getLogger(__name__)


class SBPBank:
    """Справочник банков СБП.

    BIC коды банков-участников СБП.
    """

    BANKS: Dict[str, str] = {
        "sberbank": "044525225",
        "tinkoff": "044525974",
        "alfa": "044525593",
        "vtb": "044525187",
        "gazprombank": "044525823",
        "raiffeisen": "044525700",
        "rosbank": "044525749",
        "open": "044525756",
        "post_bank": "044525914",
        "home_credit": "044525366",
        "otp": "044525354",
        "uralsib": "044525787",
        "renessans": "044525497",
        "sovcombank": "044525396",
        "psb": "044525236",
        "ak_bars": "044525805",
        "vozrozhdenie": "044525105",
        "zapsibkombank": "044525512",
        "kredit_europe": "044525776",
    }

    @classmethod
    def get_bic(cls, bank_code: str) -> Optional[str]:
        """Получить BIC код банка."""
        return cls.BANKS.get(bank_code.lower())

    @classmethod
    def get_all_banks(cls) -> List[Dict[str, str]]:
        """Получить список всех банков."""
        return [
            {"code": code, "name": code.replace("_", " ").title(), "bic": bic}
            for code, bic in cls.BANKS.items()
        ]


class SBPStatus(str, Enum):
    """Статусы платежей СБП."""

    PENDING = "PENDING"  # Ожидает оплаты
    PAID = "PAID"  # Оплачен
    REJECTED = "REJECTED"  # Отклонён
    EXPIRED = "EXPIRED"  # Истёк срок действия
    REFUNDED = "REFUNDED"  # Возвращён
    PARTIAL_REFUNDED = "PARTIAL_REFUNDED"  # Частично возвращён


class SBPGateway(BasePaymentGateway):
    """СБП платёжный шлюз.

    Поддерживает:
    - Создание платежей по номеру телефона
    - Проверку статуса платежа
    - Возврат платежей (refund)
    - Webhook уведомления

    Пример использования:
        gateway = SBPGateway()
        result = await gateway.create_payment(
            amount=1000,
            order_id="order_123",
            phone="+79991234567"
        )
    """

    API_BASE_URL = "https://api.sbp.nspk.ru"
    API_VERSION = "v1"

    def __init__(self) -> None:
        """Инициализация СБП gateway."""
        super().__init__(
            api_key=settings.sbp_api_key,
            secret_key=settings.sbp_secret_key,
            return_url=settings.sbp_return_url,
            base_url=f"{self.API_BASE_URL}/{self.API_VERSION}",
        )
        self.merchant_id = settings.sbp_merchant_id

    def validate_config(self) -> bool:
        """Проверка конфигурации СБП gateway."""
        if not self.merchant_id:
            logger.error("SBP: merchant_id not configured")
            return False
        if not self.api_key:
            logger.error("SBP: API key not configured")
            return False
        if not self.secret_key:
            logger.warning("SBP: secret key not configured")
        return True

    def generate_signature(
        self,
        method: str,
        path: str,
        timestamp: str,
        body: Optional[str] = None,
    ) -> str:
        """Генерация подписи для СБП API.

        СБП использует HMAC-SHA256 подпись с форматом:
        {method}:{path}:{timestamp}:{body_hash}

        Args:
            method: HTTP метод (GET, POST, etc.)
            path: Путь API (без базового URL)
            timestamp: ISO 8601 timestamp
            body: Тело запроса (JSON строка)

        Returns:
            Подпись в base64
        """
        import base64

        # Хэш тела запроса
        if body:
            body_hash = hashlib.sha256(body.encode()).hexdigest().lower()
        else:
            body_hash = hashlib.sha256(b"").hexdigest().lower()

        # Строка для подписи
        signature_str = f"{method.upper()}:{path}:{timestamp}:{body_hash}"

        # HMAC-SHA256 подпись
        signature = hmac.new(
            self.secret_key.encode(),
            signature_str.encode(),
            hashlib.sha256,
        ).digest()

        return base64.b64encode(signature).decode()

    async def _authenticated_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Выполнение авторизованного запроса к СБП API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        # Генерация timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Генерация подписи
        body = json.dumps(json_data, separators=(",", ":")) if json_data else None
        signature = self.generate_signature(method, endpoint, timestamp, body)

        # Заголовки
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Signature": signature,
            "X-Merchant-Id": self.merchant_id,
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
        self,
        amount: float,
        description: str,
        order_id: str,
        phone: Optional[str] = None,
        bank_bic: Optional[str] = None,
        expiration_minutes: int = 30,
    ) -> Dict[str, Any]:
        """Создание платежа СБП.

        Args:
            amount: Сумма платежа в рублях
            description: Описание платежа
            order_id: Уникальный идентификатор заказа
            phone: Номер телефона получателя (опционально)
            bank_bic: BIC код банка получателя (опционально)
            expiration_minutes: Время действия ссылки (минуты)

        Returns:
            Информация о платеже с payment_url
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        if amount <= 0:
            raise PaymentGatewayError("Amount must be positive")

        payload = {
            "amount": amount,
            "currency": "RUB",
            "merchantId": self.merchant_id,
            "orderId": order_id,
            "description": description[:250],
            "expiration": expiration_minutes,
            "returnUrl": self.return_url,
        }

        if phone:
            # Очистка номера телефона
            clean_phone = "".join(c for c in phone if c.isdigit())
            if clean_phone.startswith("8"):
                clean_phone = "7" + clean_phone[1:]
            payload["phone"] = f"+{clean_phone}"

        if bank_bic:
            payload["bankBic"] = bank_bic

        result = await self._authenticated_request("POST", "/payments", json_data=payload)

        return {
            "payment_id": result.get("id"),
            "order_id": order_id,
            "amount": amount,
            "currency": "RUB",
            "status": result.get("status", SBPStatus.PENDING.value),
            "payment_url": result.get("paymentUrl"),
            "qr_code": result.get("qrCode"),  # Base64 QR кода
            "expires_at": result.get("expiresAt"),
            "created_at": result.get("createdAt"),
        }

    async def get_payment_info(self, payment_id: str) -> Dict[str, Any]:
        """Получение информации о платеже.

        Args:
            payment_id: Идентификатор платежа

        Returns:
            Информация о платеже
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        result = await self._authenticated_request("GET", f"/payments/{payment_id}")

        return {
            "payment_id": result.get("id"),
            "order_id": result.get("orderId"),
            "amount": result.get("amount"),
            "currency": result.get("currency", "RUB"),
            "status": result.get("status"),
            "phone": result.get("phone"),
            "bank_bic": result.get("bankBic"),
            "created_at": result.get("createdAt"),
            "paid_at": result.get("paidAt"),
            "expires_at": result.get("expiresAt"),
        }

    async def get_payment_by_order_id(self, order_id: str) -> Dict[str, Any]:
        """Получение информации о платеже по order_id.

        Args:
            order_id: Идентификатор заказа

        Returns:
            Информация о платеже
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        result = await self._authenticated_request(
            "GET", "/payments", params={"orderId": order_id}
        )

        if result and isinstance(result, list) and len(result) > 0:
            return self.get_payment_info(result[0].get("id"))

        raise PaymentGatewayError(f"Payment not found for order: {order_id}")

    async def refund_payment(
        self,
        payment_id: str,
        amount: Optional[float] = None,
        reason: str = "Refund",
    ) -> Dict[str, Any]:
        """Возврат платежа.

        Args:
            payment_id: Идентификатор платежа
            amount: Сумма возврата (полная если не указана)
            reason: Причина возврата

        Returns:
            Информация о возврате
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        payload = {
            "reason": reason[:250],
        }

        if amount:
            payload["amount"] = amount

        result = await self._authenticated_request(
            "POST", f"/payments/{payment_id}/refund", json_data=payload
        )

        return {
            "refund_id": result.get("id"),
            "payment_id": payment_id,
            "amount": result.get("amount"),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "created_at": result.get("createdAt"),
        }

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Отмена платежа.

        Args:
            payment_id: Идентификатор платежа

        Returns:
            Результат отмены
        """
        if not self.validate_config():
            raise PaymentGatewayConfigError("SBP gateway not configured")

        result = await self._authenticated_request(
            "POST", f"/payments/{payment_id}/cancel"
        )

        return {
            "payment_id": payment_id,
            "status": result.get("status", SBPStatus.REJECTED.value),
            "cancelled_at": result.get("cancelledAt"),
        }

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        timestamp: str,
    ) -> bool:
        """Проверка подписи webhook уведомления.

        Args:
            payload: Сырые данные webhook (bytes)
            signature: Подпись из заголовка X-Signature
            timestamp: Timestamp из заголовка X-Timestamp

        Returns:
            True если подпись валидна
        """
        if not self.secret_key:
            logger.warning("SBP: secret key not configured, skipping signature verification")
            return True

        # Проверяем timestamp (не старше 5 минут)
        try:
            webhook_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            time_diff = abs((now - webhook_time).total_seconds())
            if time_diff > 300:  # 5 минут
                logger.warning(f"SBP webhook timestamp too old: {time_diff}s")
                return False
        except Exception as e:
            logger.warning(f"SBP webhook timestamp parse error: {e}")
            return False

        # Генерируем ожидаемую подпись
        body_hash = hashlib.sha256(payload).hexdigest().lower()
        signature_str = f"POST:/webhooks:{timestamp}:{body_hash}"

        expected_signature = hmac.new(
            self.secret_key.encode(),
            signature_str.encode(),
            hashlib.sha256,
        ).digest()

        import base64
        expected_b64 = base64.b64encode(expected_signature).decode()

        return hmac.compare_digest(expected_b64, signature)

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str,
        timestamp: str,
    ) -> Dict[str, str]:
        """Обработка webhook уведомления от СБП.

        Args:
            payload: Данные webhook уведомления
            signature: Подпись из заголовка X-Signature
            timestamp: Timestamp из заголовка X-Timestamp

        Returns:
            Результат обработки webhook
        """
        # Проверяем подпись
        raw_payload = json.dumps(payload, separators=(",", ":")).encode()
        if not self.verify_webhook_signature(raw_payload, signature, timestamp):
            logger.warning("Invalid SBP webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event_type = payload.get("event", "")
        payment_data = payload.get("payment", {})
        payment_id = payment_data.get("id")
        status = payment_data.get("status", "")

        logger.info(f"Processing SBP webhook event: {event_type} for payment {payment_id}")

        result = {
            "event_type": event_type,
            "payment_id": payment_id,
            "status": status,
            "processed": True,
        }

        # Обработка различных типов событий
        if event_type == "payment.paid":
            result["message"] = "Payment successful"
            result["action"] = "fulfill_order"

        elif event_type == "payment.rejected":
            result["message"] = "Payment rejected"
            result["action"] = "cancel_order"

        elif event_type == "payment.expired":
            result["message"] = "Payment expired"
            result["action"] = "expire_order"

        elif event_type == "payment.refunded":
            result["message"] = "Payment refunded"
            result["action"] = "process_refund"

        else:
            logger.info(f"Unhandled SBP webhook event: {event_type}")
            result["message"] = f"Event {event_type} acknowledged"
            result["action"] = "acknowledge"

        return result

    def get_qr_code_url(self, payment_id: str) -> str:
        """Получить URL QR кода для платежа.

        Args:
            payment_id: Идентификатор платежа

        Returns:
            URL для скачивания QR кода
        """
        return f"{self.base_url}/payments/{payment_id}/qr"


# Глобальный экземпляр gateway
gateway = SBPGateway()

# Экспортируемые функции
create_payment = gateway.create_payment
get_payment_info = gateway.get_payment_info
get_payment_by_order_id = gateway.get_payment_by_order_id
refund_payment = gateway.refund_payment
cancel_payment = gateway.cancel_payment
verify_webhook_signature = gateway.verify_webhook_signature
handle_sbp_webhook = gateway.handle_webhook
get_all_banks = SBPBank.get_all_banks
get_bank_bic = SBPBank.get_bic
