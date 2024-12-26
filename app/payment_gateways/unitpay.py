'''
Код с подключением UnitPay
'''

import hashlib
import hmac
import requests
from app.config import UNITPAY_API_KEY, UNITPAY_SECRET_KEY

def generate_signature(params: dict) -> str:
    """
    Генерация подписи для запроса в UnitPay.
    
    :param params: Параметры запроса.
    :return: Подпись для запроса.
    """
    # Собираем строку для подписи
    signature_str = '&'.join(f"{key}={value}" for key, value in sorted(params.items()))
    signature_str += f"&secret={UNITPAY_SECRET_KEY}"

    # Генерация HMAC подписи с использованием SHA-256
    return hmac.new(UNITPAY_SECRET_KEY.encode(), signature_str.encode(), hashlib.sha256).hexdigest()

def create_payment(amount: float, description: str, order_id: str):
    """
    Создание платежа через UnitPay API.
    
    :param amount: Сумма платежа.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от UnitPay.
    """
    url = "https://unitpay.ru/api/payment"
    headers = {
        "Authorization": f"Bearer {UNITPAY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description,
        "order_id": order_id,  # Уникальный идентификатор заказа
        "return_url": "https://yourwebsite.com/payment/return"  # URL для возврата после оплаты
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

def verify_signature(params: dict, provided_signature: str) -> bool:
    """
    Проверка подписи при обработке webhook уведомления.
    
    :param params: Параметры уведомления.
    :param provided_signature: Подпись, переданная с уведомлением.
    :return: True, если подписи совпадают, False — если нет.
    """
    expected_signature = generate_signature(params)
    return hmac.compare_digest(expected_signature, provided_signature)

async def handle_unitpay_webhook(payload: dict, signature: str) -> dict:
    """
    Обработка webhook уведомления с проверкой подписи.
    
    :param payload: Данные уведомления.
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
