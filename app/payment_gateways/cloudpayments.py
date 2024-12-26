'''
Код с подключением CloudPayments
'''

import hmac
import hashlib
import base64
import os

SECRET_KEY = os.getenv("SECRET_KEY")  # Используйте секретный ключ для подписи

def generate_token(order_id: str) -> str:
    """
    Генерация уникального токена для защиты платежа.
    
    :param order_id: Уникальный идентификатор заказа.
    :return: Строка токена.
    """
    # Генерация токена с использованием HMAC и SHA-256
    message = f"{order_id}{SECRET_KEY}"
    token = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    return token

def create_payment(amount: float, description: str, order_id: str):
    """
    Создание платежа через API CloudPayments с добавлением уникального токена.
    
    :param amount: Сумма платежа.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от CloudPayments.
    """
    url = "https://api.cloudpayments.ru/payments"
    headers = {
        "Authorization": f"Bearer {CLOUDPAYMENTS_API_KEY}",
        "Content-Type": "application/json"
    }

    token = generate_token(order_id)  # Генерация токена для защиты

    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description,
        "order_id": order_id,
        "return_url": f"https://yourwebsite.com/payment/return?token={token}",  # URL с токеном
        "invoice_id": f"inv_{order_id}",
        "payment_type": "BANK_CARD",
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to create payment", "details": response.json()}
    except requests.exceptions.RequestException as e:
        return {"error": "Request failed", "details": str(e)}

def verify_token(order_id: str, token: str) -> bool:
    """
    Проверка токена при возврате с платежа.
    
    :param order_id: Уникальный идентификатор заказа.
    :param token: Токен, полученный в URL.
    :return: True, если токен верен, False — если нет.
    """
    expected_token = generate_token(order_id)
    return hmac.compare_digest(expected_token, token)

async def handle_cloudpayments_webhook(payload: dict, token: str) -> dict:
    """
    Обработка webhook уведомления с проверкой токена.
    
    :param payload: Данные уведомления.
    :param token: Токен, переданный в URL.
    :return: Результат обработки уведомления.
    """
    order_id = payload.get("order_id")
    if not verify_token(order_id, token):
        return {"status": "failed", "message": "Invalid token"}
    
    if payload.get("event") == "payment.succeeded":
        return {"status": "processed", "message": "Payment successful"}
    elif payload.get("event") == "payment.canceled":
        return {"status": "processed", "message": "Payment canceled"}
    else:
        return {"status": "ignored", "message": "Event not recognized"}
