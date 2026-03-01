"""Интеграция с платёжной системой CloudPayments."""

import hashlib
import hmac
import logging
import os
import requests
from typing import Any, Dict, Optional
from app.config import CLOUDPAYMENTS_API_KEY, CLOUDPAYMENTS_RETURN_URL

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "")
REQUEST_TIMEOUT = 30


def generate_token(order_id: str) -> str:
    """Генерация уникального токена для защиты платежа."""
    if not SECRET_KEY:
        logger.warning("SECRET_KEY is not configured")
        return ""

    message = f"{order_id}{SECRET_KEY}"
    return hmac.new(
        SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


def create_payment(
    amount: float,
    description: str,
    order_id: str
) -> Dict[str, Any]:
    """
    Создание платежа через API CloudPayments.

    :param amount: Сумма платежа.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от CloudPayments или ошибка.
    """
    if not CLOUDPAYMENTS_API_KEY:
        logger.error("CLOUDPAYMENTS_API_KEY is not configured")
        return {"error": "Payment gateway not configured"}

    if amount <= 0:
        return {"error": "Invalid amount", "details": "Amount must be positive"}

    url = "https://api.cloudpayments.ru/payments"
    headers = {
        "Authorization": f"Bearer {CLOUDPAYMENTS_API_KEY}",
        "Content-Type": "application/json"
    }

    token = generate_token(order_id)
    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description[:250],
        "order_id": order_id,
        "return_url": f"{CLOUDPAYMENTS_RETURN_URL}?token={token}",
        "invoice_id": f"inv_{order_id}",
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
        logger.error(f"CloudPayments HTTP error: {e}")
        try:
            error_detail = e.response.json()
        except Exception:
            error_detail = str(e)
        return {"error": "Payment request failed", "details": error_detail}

    except requests.exceptions.Timeout:
        logger.error("CloudPayments request timeout")
        return {"error": "Payment gateway timeout"}

    except requests.exceptions.RequestException as e:
        logger.error(f"CloudPayments request failed: {e}")
        return {"error": "Payment request failed", "details": str(e)}


def verify_token(order_id: str, token: str) -> bool:
    """Проверка токена при возврате с платежа."""
    if not SECRET_KEY:
        logger.warning("SECRET_KEY is not configured, skipping token verification")
        return True

    expected_token = generate_token(order_id)
    return hmac.compare_digest(expected_token, token)


async def handle_cloudpayments_webhook(
    payload: Dict[str, Any],
    token: str
) -> Dict[str, str]:
    """
    Обработка webhook уведомления от CloudPayments.

    :param payload: Данные уведомления.
    :param token: Токен уведомления.
    :return: Результат обработки.
    """
    order_id = payload.get("order_id", "")
    if not verify_token(order_id, token):
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
