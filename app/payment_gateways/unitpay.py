'''
Код с подключением UnitPay
'''

import requests
from app.config import UNITPAY_API_KEY

def create_payment(amount: float, description: str, order_id: str):
    """
    Создание платежа через UnitPay API.

    :param amount: Сумма платежа в рублях.
    :param description: Описание платежа.
    :param order_id: Уникальный идентификатор заказа.
    :return: Ответ от UnitPay (JSON).
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
        "order_id": order_id, # Уникальный идентификатор заказа
        "return_url": "https://yourwebsite.com/payment/return" # URL для возврата после оплаты
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status() # Проверка на успешный статус ответа (HTTP 2xx)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to create payment", "details": response.json()}
    except requests.exceptions.RequestException as e:
        # Логирование ошибки
        return {"error": "Request failed", "details": str(e)}
