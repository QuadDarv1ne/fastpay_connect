'''
Код с подключением Robokassa
'''

import requests
from app.config import ROBOKASSA_API_KEY

def create_payment(amount: float, description: str, order_id: str):
    """
    Создание платежа через API Робокасса.

    :param amount: Сумма платежа в рублях.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от Робокассы (JSON).
    """
    url = "https://api.robokassa.ru/payment"
    headers = {
        "Authorization": f"Bearer {ROBOKASSA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "amount": amount,
        "currency": "RUB",
        "description": description,
        "order_id": order_id, # Уникальный идентификатор заказа
        "return_url": "https://yourwebsite.com/payment/return", # URL для возврата после оплаты
        "invoice_id": f"inv_{order_id}", # Уникальный идентификатор счета
        "payment_type": "BANK_CARD", # Тип платежа (например, банковская карта)
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Проверка на успешный статус ответа (HTTP 2xx)
        
        if response.status_code == 200:
            return response.json() # Возвращаем JSON-ответ от Робокассы
        else:
            return {"error": "Failed to create payment", "details": response.json()}
    except requests.exceptions.RequestException as e:
        # Логирование ошибки
        return {"error": "Request failed", "details": str(e)}

async def handle_robokassa_webhook(payload: dict) -> dict:
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
