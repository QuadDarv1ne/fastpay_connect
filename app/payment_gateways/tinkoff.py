"""Интеграция с платёжной системой Tinkoff."""

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from app.payment_gateways.base import BasePaymentGateway
from app.payment_gateways.exceptions import PaymentGatewayConfigError
from app.settings import settings

logger = logging.getLogger(__name__)


class TinkoffGateway(BasePaymentGateway):
    """Tinkoff платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=settings.tinkoff_api_key,
            secret_key=settings.tinkoff_secret_key,
            return_url=settings.tinkoff_return_url,
            base_url="https://api.tinkoff.ru/v2",
        )

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через Tinkoff."""
        payload = self._prepare_payment_payload(amount, description, order_id)
        payload["payment_type"] = "BANK_CARD"
        payload["TerminalKey"] = self.api_key

        headers = {
            "Content-Type": "application/json",
        }

        return await self._request(
            "POST", f"{self.base_url}/Init", headers=headers, json_data=payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от Tinkoff."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid Tinkoff webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing Tinkoff webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored Tinkoff event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}

    async def refund_payment(
        self, payment_id: str, amount: Optional[float] = None, reason: str = ""
    ) -> Dict[str, Any]:
        """Возврат платежа через Tinkoff API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("Tinkoff gateway not configured")

        if amount is None or amount <= 0:
            raise ValueError("Refund amount must be specified and positive")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        refund_payload: Dict[str, Any] = {
            "TerminalKey": self.api_key,
            "PaymentId": payment_id,
            "Amount": int(Decimal(str(amount)) * 100),  # Tinkoff uses kopecks; Decimal avoids float imprecision
            "Description": reason[:250] if reason else "Refund",
        }

        return await self._request(
            "POST", f"{self.base_url}/Refund", headers=headers, json_data=refund_payload
        )

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Отмена платежа через Tinkoff API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("Tinkoff gateway not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        cancel_payload = {
            "TerminalKey": self.api_key,
            "PaymentId": payment_id,
        }

        return await self._request(
            "POST", f"{self.base_url}/Cancel", headers=headers, json_data=cancel_payload
        )


gateway = TinkoffGateway()
create_payment = gateway.create_payment
verify_signature = gateway.verify_signature
handle_tinkoff_webhook = gateway.handle_webhook
refund_payment = gateway.refund_payment
cancel_payment = gateway.cancel_payment
