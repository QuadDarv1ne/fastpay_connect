"""Интеграция с платёжной системой UnitPay."""

import logging
from typing import Any, Dict, Optional

from app.payment_gateways.base import BasePaymentGateway
from app.payment_gateways.exceptions import PaymentGatewayConfigError
from app.settings import settings

logger = logging.getLogger(__name__)


class UnitPayGateway(BasePaymentGateway):
    """UnitPay платёжный шлюз."""

    def __init__(self):
        super().__init__(
            api_key=settings.unitpay_api_key,
            secret_key=settings.unitpay_secret_key,
            return_url=settings.unitpay_return_url,
            base_url="https://unitpay.ru/api",
        )

    async def create_payment(
        self, amount: float, description: str, order_id: str
    ) -> Dict[str, Any]:
        """Создание платежа через UnitPay."""
        payload = self._prepare_payment_payload(amount, description, order_id)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        unitpay_payload = {
            **payload,
            "return_url": self.return_url,
        }

        return await self._request(
            "POST", f"{self.base_url}/payment", headers=headers, json_data=unitpay_payload
        )

    async def handle_webhook(
        self, payload: Dict[str, Any], signature: str
    ) -> Dict[str, str]:
        """Обработка webhook от UnitPay."""
        if not self.verify_signature(payload, signature):
            logger.warning("Invalid UnitPay webhook signature")
            return {"status": "failed", "message": "Invalid signature"}

        event = payload.get("event", "")
        logger.info(f"Processing UnitPay webhook event: {event}")

        if event == "payment.succeeded":
            return {"status": "processed", "message": "Payment successful"}
        elif event == "payment.canceled":
            return {"status": "processed", "message": "Payment canceled"}
        elif event == "payment.refunded":
            return {"status": "processed", "message": "Payment refunded"}
        else:
            logger.info(f"Ignored UnitPay event: {event}")
            return {"status": "ignored", "message": "Event not recognized"}

    async def refund_payment(
        self, payment_id: str, amount: Optional[float] = None, reason: str = ""
    ) -> Dict[str, Any]:
        """Возврат платежа через UnitPay API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("UnitPay gateway not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        refund_payload: Dict[str, Any] = {
            "paymentId": payment_id,
        }
        if amount:
            refund_payload["amount"] = amount
        if reason:
            refund_payload["reason"] = reason[:250]

        return await self._request(
            "POST", f"{self.base_url}/refund", headers=headers, json_data=refund_payload
        )

    async def cancel_payment(self, payment_id: str) -> Dict[str, Any]:
        """Отмена платежа через UnitPay API."""
        if not self.validate_config():
            raise PaymentGatewayConfigError("UnitPay gateway not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        return await self._request(
            "POST",
            f"{self.base_url}/cancel",
            headers=headers,
            json_data={"paymentId": payment_id},
        )


gateway = UnitPayGateway()
create_payment = gateway.create_payment
verify_signature = gateway.verify_signature
handle_unitpay_webhook = gateway.handle_webhook
refund_payment = gateway.refund_payment
cancel_payment = gateway.cancel_payment
