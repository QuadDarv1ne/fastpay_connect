"""Central registry for payment gateway configurations and shared utilities."""

from typing import Any, Dict, Optional
import uuid

from app.payment_gateways.yookassa import (
    create_payment as yookassa_create,
    handle_yookassa_webhook,
    refund_payment as yookassa_refund,
    cancel_payment as yookassa_cancel,
)
from app.payment_gateways.tinkoff import (
    create_payment as tinkoff_create,
    handle_tinkoff_webhook,
    refund_payment as tinkoff_refund,
    cancel_payment as tinkoff_cancel,
)
from app.payment_gateways.cloudpayments import (
    create_payment as cloudpayments_create,
    handle_cloudpayments_webhook,
    refund_payment as cloudpayments_refund,
    cancel_payment as cloudpayments_cancel,
)
from app.payment_gateways.unitpay import (
    create_payment as unitpay_create,
    handle_unitpay_webhook,
    refund_payment as unitpay_refund,
    cancel_payment as unitpay_cancel,
)
from app.payment_gateways.robokassa import (
    create_payment as robokassa_create,
    handle_robokassa_webhook,
    refund_payment as robokassa_refund,
    cancel_payment as robokassa_cancel,
)
from app.payment_gateways.sbp import (
    create_payment as sbp_create,
    handle_sbp_webhook,
    refund_payment as sbp_refund,
    cancel_payment as sbp_cancel,
)
from app.payment_gateways.rustore import (
    create_payment as rustore_create,
    handle_rustore_webhook,
    refund_payment as rustore_refund,
    cancel_payment as rustore_cancel,
)
from app.payment_gateways.apple_pay import (
    create_payment as apple_pay_create,
    handle_apple_pay_webhook,
    refund_payment as apple_pay_refund,
    cancel_payment as apple_pay_cancel,
)
from app.payment_gateways.google_pay import (
    create_payment as google_pay_create,
    handle_google_pay_webhook,
    refund_payment as google_pay_refund,
    cancel_payment as google_pay_cancel,
)


def extract_nested_value(data: Dict[str, Any], path: str) -> Optional[Any]:
    """Extract a nested value from a dict by dot-separated path."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def generate_order_id() -> str:
    """Generate a unique order_id."""
    return str(uuid.uuid4())


def extract_webhook_event_id(payload: Dict[str, Any]) -> Optional[str]:
    """Extract event_id from webhook payload for idempotency."""
    return payload.get("event_id") or payload.get("id") or payload.get("transaction_id")


GATEWAY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "yookassa": {
        "name": "yookassa",
        "create_func": yookassa_create,
        "refund_func": yookassa_refund,
        "cancel_func": yookassa_cancel,
        "payment_id_field": "id",
        "payment_url_field": "confirmation.confirmation_url",
    },
    "tinkoff": {
        "name": "tinkoff",
        "create_func": tinkoff_create,
        "refund_func": tinkoff_refund,
        "cancel_func": tinkoff_cancel,
        "payment_id_field": "payment_id",
        "payment_url_field": "payment_url",
    },
    "cloudpayments": {
        "name": "cloudpayments",
        "create_func": cloudpayments_create,
        "refund_func": cloudpayments_refund,
        "cancel_func": cloudpayments_cancel,
        "payment_id_field": "transaction_id",
    },
    "unitpay": {
        "name": "unitpay",
        "create_func": unitpay_create,
        "refund_func": unitpay_refund,
        "cancel_func": unitpay_cancel,
        "payment_id_field": "payment_id",
    },
    "robokassa": {
        "name": "robokassa",
        "create_func": robokassa_create,
        "refund_func": robokassa_refund,
        "cancel_func": robokassa_cancel,
        "payment_id_field": "invoice_id",
    },
    "sbp": {
        "name": "sbp",
        "create_func": sbp_create,
        "refund_func": sbp_refund,
        "cancel_func": sbp_cancel,
        "payment_id_field": "paymentId",
        "payment_url_field": "payload",
    },
    "rustore": {
        "name": "rustore",
        "create_func": rustore_create,
        "refund_func": rustore_refund,
        "cancel_func": rustore_cancel,
        "payment_id_field": "orderId",
    },
    "apple_pay": {
        "name": "apple_pay",
        "create_func": apple_pay_create,
        "refund_func": apple_pay_refund,
        "cancel_func": apple_pay_cancel,
        "payment_id_field": "payment_id",
    },
    "google_pay": {
        "name": "google_pay",
        "create_func": google_pay_create,
        "refund_func": google_pay_refund,
        "cancel_func": google_pay_cancel,
        "payment_id_field": "payment_id",
    },
}

WEBHOOK_HANDLERS: Dict[str, Any] = {
    "yookassa": handle_yookassa_webhook,
    "tinkoff": handle_tinkoff_webhook,
    "cloudpayments": handle_cloudpayments_webhook,
    "unitpay": handle_unitpay_webhook,
    "robokassa": handle_robokassa_webhook,
    "sbp": handle_sbp_webhook,
    "rustore": handle_rustore_webhook,
    "apple_pay": handle_apple_pay_webhook,
    "google_pay": handle_google_pay_webhook,
}

EVENT_STATUS_MAP: Dict[str, str] = {
    "payment.succeeded": "completed",
    "payment.canceled": "cancelled",
    "payment.cancelled": "cancelled",
    "payment.failed": "failed",
    "payment.refunded": "refunded",
    "payment.waiting_for_capture": "processing",
    "payment.waiting": "pending",
    "order.completed": "completed",
    "order.cancelled": "cancelled",
    "subscription.activated": "completed",
    "subscription.cancelled": "cancelled",
}

STATUS_MAP: Dict[str, str] = {
    "payment successful": "completed",
    "payment canceled": "cancelled",
    "payment failed": "failed",
    "payment refunded": "refunded",
}
