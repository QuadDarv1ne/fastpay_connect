"""Central registry for payment gateway configurations and shared utilities."""

from typing import Any, Dict, Optional
import uuid

from app.payment_gateways.yookassa import (
    create_payment as yookassa_create,
    handle_yookassa_webhook,
)
from app.payment_gateways.tinkoff import (
    create_payment as tinkoff_create,
    handle_tinkoff_webhook,
)
from app.payment_gateways.cloudpayments import (
    create_payment as cloudpayments_create,
    handle_cloudpayments_webhook,
)
from app.payment_gateways.unitpay import (
    create_payment as unitpay_create,
    handle_unitpay_webhook,
)
from app.payment_gateways.robokassa import (
    create_payment as robokassa_create,
    handle_robokassa_webhook,
)
from app.payment_gateways.sbp import (
    create_payment as sbp_create,
    handle_sbp_webhook,
)
from app.payment_gateways.rustore import (
    create_payment as rustore_create,
    handle_rustore_webhook,
)
from app.payment_gateways.apple_pay import (
    create_payment as apple_pay_create,
    handle_apple_pay_webhook,
)
from app.payment_gateways.google_pay import (
    create_payment as google_pay_create,
    handle_google_pay_webhook,
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
        "payment_id_field": "id",
        "payment_url_field": "confirmation.confirmation_url",
    },
    "tinkoff": {
        "name": "tinkoff",
        "create_func": tinkoff_create,
        "payment_id_field": "payment_id",
        "payment_url_field": "payment_url",
    },
    "cloudpayments": {
        "name": "cloudpayments",
        "create_func": cloudpayments_create,
        "payment_id_field": "transaction_id",
    },
    "unitpay": {
        "name": "unitpay",
        "create_func": unitpay_create,
        "payment_id_field": "payment_id",
    },
    "robokassa": {
        "name": "robokassa",
        "create_func": robokassa_create,
        "payment_id_field": "invoice_id",
    },
    "sbp": {
        "name": "sbp",
        "create_func": sbp_create,
        "payment_id_field": "paymentId",
        "payment_url_field": "payload",
    },
    "rustore": {
        "name": "rustore",
        "create_func": rustore_create,
        "payment_id_field": "orderId",
    },
    "apple_pay": {
        "name": "apple_pay",
        "create_func": apple_pay_create,
        "payment_id_field": "payment_id",
    },
    "google_pay": {
        "name": "google_pay",
        "create_func": google_pay_create,
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

STATUS_MAP: Dict[str, str] = {
    "payment successful": "completed",
    "payment canceled": "cancelled",
    "payment failed": "failed",
    "payment refunded": "refunded",
}
