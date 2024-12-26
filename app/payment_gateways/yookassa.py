'''
Код с подключением YooKassa
'''

import hashlib
import hmac
import requests
from app.config import YOOKASSA_API_KEY, YOOKASSA_SECRET_KEY

# Функция для генерации подписи
def generate_signature(params: dict) -> str:
    """
    Генерация подписи для запроса в YooKassa.
    
    :param params: Параметры запроса.
    :return: Подпись для запроса.
    """
    signature_str = '&'.join(f"{key}={value}" for key, value in sorted(params.items()))
    signature_str += f"&secret={YOOKASSA_SECRET_KEY}"
    return hmac.new(YOOKASSA_SECRET_KEY.encode(), signature_str.encode(), hashlib.sha256).hexdigest()


# Функция для создания платежа
def create_payment(amount: float, description: str):
    """
    Создание платежа через API YooKassa с подписью.
    
    :param amount: Сумма платежа в рублях.
    :param description: Описание платежа.
    :return: Ответ от YooKassa (JSON).
    """
    url = "https://api.yookassa.ru/v3/payment"
    headers = {
        "Authorization": f"Bearer {YOOKASSA_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": {
            "value": amount,
            "currency": "RUB"
        },
        "capture_mode": "AUTOMATIC",
        "confirmation": {
            "type": "redirect",
            "return_url": "https://yourwebsite.com/payment/return"
        },
        "description": description
    }

    # Генерация подписи для безопасности
    payload["signature"] = generate_signature(payload)

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Проверка на успешный статус ответа (HTTP 2xx)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to create payment", "details": response.json()}
    except requests.exceptions.RequestException as e:
        return {"error": "Request failed", "details": str(e)}


# Функция для проверки подписи
def verify_signature(params: dict, provided_signature: str) -> bool:
    """
    Проверка подписи при обработке webhook уведомления.
    
    :param params: Параметры уведомления.
    :param provided_signature: Подпись, переданная с уведомлением.
    :return: True, если подписи совпадают, False — если нет.
    """
    expected_signature = generate_signature(params)
    return hmac.compare_digest(expected_signature, provided_signature)


# Функция для обработки webhook уведомления
async def handle_yookassa_webhook(payload: dict, signature: str) -> dict:
    """
    Обработка webhook уведомления от YooKassa с проверкой подписи.
    
    :param payload: Данные уведомления от YooKassa.
    :param signature: Подпись, полученная с уведомлением.
    :return: Результат обработки уведомления.
    """
    # Проверка подписи
    if not verify_signature(payload, signature):
        return {"status": "failed", "message": "Invalid signature"}

    if payload.get("event") == "payment.succeeded":
        return {"status": "processed", "message": "Payment successful"}
    elif payload.get("event") == "payment.canceled":
        return {"status": "processed", "message": "Payment canceled"}
    else:
        return {"status": "ignored", "message": "Event not recognized"}
