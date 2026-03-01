"""Интеграция с платёжной системой YooKassa."""

import hashlib
import hmac
import logging
import requests
from typing import Any, Dict, Optional
from app.config import YOOKASSA_API_KEY, YOOKASSA_SECRET_KEY, YOOKASSA_RETURN_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


def generate_signature(params: Dict[str, Any]) -> str:
    """
    Генерация подписи для запроса в YooKassa.

    :param params: Параметры запроса.
    :return: Подпись для запроса.
    """
    if not YOOKASSA_SECRET_KEY:
        logger.warning("YOOKASSA_SECRET_KEY is not configured")
        return ""

    signature_str = '&'.join(
        f"{key}={value}" for key, value in sorted(params.items())
    )
    signature_str += f"&secret={YOOKASSA_SECRET_KEY}"
    return hmac.new(
        YOOKASSA_SECRET_KEY.encode(),
        signature_str.encode(),
        hashlib.sha256
    ).hexdigest()


def create_payment(
    amount: float,
    description: str,
    order_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Создание платежа через API YooKassa.

    :param amount: Сумма платежа в рублях.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа (опционально).
    :return: Ответ от YooKassa или ошибка.
    """
    if not YOOKASSA_API_KEY:
        logger.error("YOOKASSA_API_KEY is not configured")
        return {"error": "Payment gateway not configured"}

    if amount <= 0:
        return {"error": "Invalid amount", "details": "Amount must be positive"}

    url = "https://api.yookassa.ru/v3/payment"
    headers = {
        "Authorization": f"Bearer {YOOKASSA_API_KEY}",
        "Content-Type": "application/json",
        "Idempotence-Key": order_id or f"req_{hash(f'{amount}{description}')}"
    }

    payload = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "capture_mode": "AUTOMATIC",
        "confirmation": {
            "type": "redirect",
            "return_url": YOOKASSA_RETURN_URL
        },
        "description": description[:250]
    }

    if order_id:
        payload["order_id"] = order_id

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
        logger.error(f"YooKassa HTTP error: {e} - {e.response.text if hasattr(e.response, 'text') else ''}")
        try:
            error_detail = e.response.json()
        except Exception:
            error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        return {"error": "Payment request failed", "details": error_detail}

    except requests.exceptions.Timeout:
        logger.error("YooKassa request timeout")
        return {"error": "Payment gateway timeout"}

    except requests.exceptions.RequestException as e:
        logger.error(f"YooKassa request failed: {e}")
        return {"error": "Payment request failed", "details": str(e)}


def verify_signature(params: Dict[str, Any], provided_signature: str) -> bool:
    """
    Проверка подписи при обработке webhook уведомления.

    :param params: Параметры уведомления.
    :param provided_signature: Подпись, переданная с уведомлением.
    :return: True, если подписи совпадают, False — если нет.
    """
    if not YOOKASSA_SECRET_KEY:
        logger.warning("YOOKASSA_SECRET_KEY is not configured, skipping signature verification")
        return True

    expected_signature = generate_signature(params)
    return hmac.compare_digest(expected_signature, provided_signature)


async def handle_yookassa_webhook(payload: Dict[str, Any], signature: str) -> Dict[str, str]:
    """
    Обработка webhook уведомления от YooKassa.

    :param payload: Данные уведомления от YooKassa.
    :param signature: Подпись, полученная с уведомлением.
    :return: Результат обработки уведомления.
    """
    if not verify_signature(payload, signature):
        logger.warning("Invalid YooKassa webhook signature")
        return {"status": "failed", "message": "Invalid signature"}

    event = payload.get("event", "")
    logger.info(f"Processing YooKassa webhook event: {event}")

    if event == "payment.succeeded":
        return {"status": "processed", "message": "Payment successful"}
    elif event == "payment.canceled":
        return {"status": "processed", "message": "Payment canceled"}
    elif event == "payment.waiting_for_capture":
        return {"status": "processed", "message": "Payment waiting for capture"}
    else:
        logger.info(f"Ignored YooKassa event: {event}")
        return {"status": "ignored", "message": "Event not recognized"}
