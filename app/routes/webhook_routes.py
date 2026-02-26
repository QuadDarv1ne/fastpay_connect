from fastapi import APIRouter, HTTPException, Request
from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook

router = APIRouter()

# Общая функция для обработки webhook уведомлений от различных платёжных систем
async def process_webhook(payment_system: str, payload: dict, signature: str) -> dict:
    """
    Общая функция для обработки webhook уведомлений от различных платёжных систем.

    :param payment_system: Название платёжной системы (например, "yookassa", "tinkoff")
    :param payload: Данные уведомления от платёжной системы
    :param signature: Подпись от платёжной системы
    :return: Результат обработки уведомления
    :raises HTTPException: В случае ошибки при обработке уведомления
    """
    try:
        if payment_system == "yookassa":
            return await handle_yookassa_webhook(payload, signature)
        elif payment_system == "tinkoff":
            return await handle_tinkoff_webhook(payload, signature)
        elif payment_system == "cloudpayments":
            return await handle_cloudpayments_webhook(payload, signature)
        elif payment_system == "unitpay":
            return await handle_unitpay_webhook(payload, signature)
        elif payment_system == "robokassa":
            return await handle_robokassa_webhook(payload, signature)
        else:
            raise HTTPException(status_code=400, detail="Unknown payment system")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing webhook: {str(e)}")


# Обработка webhook уведомлений от различных платёжных систем
@router.post("/yookassa")
async def yookassa_webhook(request: Request):
    """
    Обрабатывает webhook уведомления от YooKassa (бывшая Яндекс.Касса).

    :param request: Запрос от YooKassa с данными уведомления
    :return: Статус и сообщение о результате обработки
    :raises HTTPException: В случае ошибки обработки
    """
    payload = await request.json()
    # Извлекаем подпись из заголовка
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("yookassa", payload, signature)
    return {"status": "success", "message": result}


# Обработка webhook уведомлений от различных платёжных систем
@router.post("/tinkoff")
async def tinkoff_webhook(request: Request):
    """
    Обрабатывает webhook уведомления от Tinkoff.

    :param request: Запрос от Tinkoff с данными уведомления
    :return: Статус и сообщение о результате обработки
    :raises HTTPException: В случае ошибки обработки
    """
    payload = await request.json()
    # Извлекаем подпись из заголовка
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("tinkoff", payload, signature)
    return {"status": "success", "message": result}


# Обработка webhook уведомлений от различных платёжных систем
@router.post("/cloudpayments")
async def cloudpayments_webhook(request: Request):
    """
    Обрабатывает webhook уведомления от CloudPayments.

    :param request: Запрос от CloudPayments с данными уведомления
    :return: Статус и сообщение о результате обработки
    :raises HTTPException: В случае ошибки обработки
    """
    payload = await request.json()
    # CloudPayments использует токен вместо подписи, извлекаем из payload
    token = payload.get("token", request.headers.get("X-Signature", ""))
    result = await process_webhook("cloudpayments", payload, token)
    return {"status": "success", "message": result}


# Обработка webhook уведомлений от различных платёжных систем
@router.post("/unitpay")
async def unitpay_webhook(request: Request):
    """
    Обрабатывает webhook уведомления от UnitPay.

    :param request: Запрос от UnitPay с данными уведомления
    :return: Статус и сообщение о результате обработки
    :raises HTTPException: В случае ошибки обработки
    """
    payload = await request.json()
    # Извлекаем подпись из заголовка
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("unitpay", payload, signature)
    return {"status": "success", "message": result}


# Обработка webhook уведомлений от различных платёжных систем
@router.post("/robokassa")
async def robokassa_webhook(request: Request):
    """
    Обрабатывает webhook уведомления от Робокасса.

    :param request: Запрос от Робокасса с данными уведомления
    :return: Статус и сообщение о результате обработки
    :raises HTTPException: В случае ошибки обработки
    """
    payload = await request.json()
    # Извлекаем подпись из заголовка
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("robokassa", payload, signature)
    return {"status": "success", "message": result}
