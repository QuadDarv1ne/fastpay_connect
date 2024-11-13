'''
Код с подключением YooKassa
'''

import requests
from app.config import YOOKASSA_API_KEY

def create_payment(amount: float, description: str):
    """
    Создание платежа через API YooKassa.

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
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Проверка на успешный статус ответа (HTTP 2xx)
        
        # Проверка ответа
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to create payment", "details": response.json()}
    except requests.exceptions.RequestException as e:
        # Логирование ошибки
        return {"error": "Request failed", "details": str(e)}

async def handle_yookassa_webhook(payload: dict) -> dict:
    """
    Обработка webhook уведомления от YooKassa.

    :param payload: Данные уведомления от YooKassa
    :return: Результат обработки уведомления
    """
    # Здесь должна быть логика для обработки уведомлений
    # Например, проверка данных в payload и обновление статуса заказа в базе данных
    # Пример:
    if payload.get("event") == "payment.succeeded":
        # Выполните необходимые действия, такие как обновление базы данных
        return {"status": "processed", "message": "Payment successful"}
    elif payload.get("event") == "payment.canceled":
        return {"status": "processed", "message": "Payment canceled"}
    else:
        return {"status": "ignored", "message": "Event not recognized"}
