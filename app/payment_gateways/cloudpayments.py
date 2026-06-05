"""Интеграция с платёжной системой CloudPayments."""

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

from app.payment_gateways.base import BasePaymentGateway
from app.payment_gateways.exceptions import PaymentGatewayConfigError
from app.settings import settings

logger = logging.getLogger(__name__)


class CloudPaymentsGateway(BasePaymentGateway):
    """CloudPayments платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=settings.cloudpayments_api_key,
            secret_key=settings.cloudpayments_secret_key,
            return_url=settings.cloudpayments_return_url,
            base_url="https://api.cloudpayments.ru",
        )

    def generate_token(self, order_id: str) -> str:
        """Генерация токена для платежа."""
        if not settings.cloudpayments_secret_key:
            logger.warning("CLOUDPAYMENTS_SECRET_KEY not configured")
            return ""

        message = f"{order_id}{settings.cloudpayments_secret_key}"
        return hmac.new(
            settings.cloudpayments_secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

    def verify_token(self, order_id: str, token: str) -> bool:
        """Проверка токена."""
        if not settings.cloudpayments_secret_key:
            logger.error(
                "CLOUDPAYMENTS_SECRET_KEY not configured, "
                "rejecting webhook token - signature verification required"
            )
            return False

        expected_token = self.generate_token(order_id)
        return hmac.compare_digest(expected_token, token)

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через CloudPayments."""
        payload = self._prepare_payment_payload(amount, description, order_id)

        token = self.generate_token(order_id)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        cloudpayments_payload = {
            "amount": amount,
            "currency": "RUB",
            "description": description[:250],
            "order_id": order_id,
            "return_url": f"{self.return_url}?token={token}",
            "invoice_id": f"inv_{order_id}",
            "payment_type": "BANK_CARD",
        }

        return await self._request(
            "POST", f"{self.base_url}/payments", headers=headers, json_data=cloudpayments_payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], token: str
    ) -> Dict[str, str]:
        """Обработка webhook от CloudPayments."""
        order_id = payload.get("order_id", "")
        if not self.verify_token(order_id, token):
            logger.warning("Invalid CloudPayments webhook token")
            return {"status": "failed", "message": "Invalid token"}

        event = payload.get("event", "")
        logger.info(f"Processing CloudPayments webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored CloudPayments event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}

    async def refund_payment(
        self, payment_id: str, amount: Optional[float] = None, reason: str = ""
    ) -> Dict[str, Any]:
        """Возврат платежа через CloudPayments API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("CloudPayments gateway not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        refund_payload: Dict[str, Any] = {
            "Amount": amount,
            "TransactionId": payment_id,
        }
        if reason:
            refund_payload["Description"] = reason[:250]

        return await self._request(
            "POST",
            f"{self.base_url}/payments/refund",
            headers=headers,
            json_data=refund_payload,
        )

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Отмена платежа через CloudPayments API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("CloudPayments gateway not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        return await self._request(
            "POST",
            f"{self.base_url}/payments/cancel",
            headers=headers,
            json_data={"TransactionId": payment_id},
        )


gateway = CloudPaymentsGateway()
create_payment = gateway.create_payment
verify_token = gateway.verify_token
handle_cloudpayments_webhook = gateway.handle_webhook
refund_payment = gateway.refund_payment
cancel_payment = gateway.cancel_payment
