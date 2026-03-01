"""Интеграция с платёжной системой Tinkoff."""

import hashlib
import hmac
import logging
import requests
from typing import Any, Dict, Optional
from app.config import TINKOFF_API_KEY, TINKOFF_SECRET_KEY, TINKOFF_RETURN_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def generate_signature(params: Dict[str, Any]) -> str:
    """Генерация подписи для запроса в Tinkoff."""
    if not TINKOFF_SECRET_KEY:
        logger.warning("TINKOFF_SECRET_KEY is not configured")
        return ""

    signature_str = '&'.join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    signature_str += f"&secret={TINKOFF_SECRET_KEY}"
    return hmac.new(
        TINKOFF_SECRET_KEY.encode(),
        signature_str.encode(),
        hashlib.sha256
    ).hexdigest()


def create_payment(
    amount: float,
    description: str,
    order_id: str
) -> Dict[str, Any]:
    """
    Создание платежа через API Tinkoff.

    :param amount: Сумма платежа.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от Tinkoff или ошибка.
    """
    if not TINKOFF_API_KEY:
        logger.error("TINKOFF_API_KEY is not configured")
        return {"error": "Payment gateway not configured"}

    if amount <= 0:
        return {"error": "Invalid amount", "details": "Amount must be positive"}

    url = "https://api.tinkoff.ru/v2/payments"
    headers = {
        "Authorization": f"Bearer {TINKOFF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description[:250],
        "order_id": order_id,
        "return_url": TINKOFF_RETURN_URL,
        "payment_type": "BANK_CARD",
    }

    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        logger.error(f"Tinkoff HTTP error: {e}")
        try:
            error_detail = e.response.json()
        except Exception:
            error_detail = str(e)
        return {"error": "Payment request failed", "details": error_detail}

    except requests.exceptions.Timeout:
        logger.error("Tinkoff request timeout")
        return {"error": "Payment gateway timeout"}

    except requests.exceptions.RequestException as e:
        logger.error(f"Tinkoff request failed: {e}")
        return {"error": "Payment request failed", "details": str(e)}


def verify_signature(params: Dict[str, Any], provided_signature: str) -> bool:
    """Проверка подписи webhook уведомления."""
    if not TINKOFF_SECRET_KEY:
        logger.warning("TINKOFF_SECRET_KEY is not configured, skipping signature verification")
        return True

    expected_signature = generate_signature(params)
    return hmac.compare_digest(expected_signature, provided_signature)


async def handle_tinkoff_webhook(
    payload: Dict[str, Any],
    signature: str
) -> Dict[str, str]:
    """
    Обработка webhook уведомления от Tinkoff.

    :param payload: Данные уведомления.
    :param signature: Подпись уведомления.
    :return: Результат обработки.
    """
    if not verify_signature(payload, signature):
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
