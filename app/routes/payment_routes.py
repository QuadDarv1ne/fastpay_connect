from fastapi import APIRouter, HTTPException
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
import asyncio

router = APIRouter()

# Создание платежа через платёжную систему
async def create_payment_gateway(payment_function, amount: float, description: str) -> dict:
    """
    Асинхронно создает платеж через переданную платёжную систему.

    Этот метод выполняет запрос к платёжной системе для создания платежа.
    Платежная функция передается в качестве аргумента, чтобы вы могли использовать
    её для разных платёжных систем.

    :param payment_function: Функция для создания платежа (например, yookassa_create)
    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от платёжной системы (например, JSON-ответ)
    :raises HTTPException: В случае ошибки при создании платежа
    """
    try:
        # Вызов функции создания платежа через платёжную систему
        return await asyncio.to_thread(payment_function, amount, description)
    except Exception as e:
        # Если произошла ошибка, возвращаем HTTPException с детальным сообщением
        raise HTTPException(status_code=400, detail=f"Error in payment gateway: {str(e)}")


# Создание платежей через разные платёжные системы
@router.post("/yookassa")
async def create_yookassa_payment(amount: float, description: str) -> dict:
    """
    Создает платеж через YooKassa (бывшая Яндекс.Касса).

    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от YooKassa о созданном платеже
    :raises HTTPException: В случае ошибки при создании платежа
    """
    return await create_payment_gateway(yookassa_create, amount, description)


# Создание платежей через разные платёжные системы
@router.post("/tinkoff")
async def create_tinkoff_payment(amount: float, description: str) -> dict:
    """
    Создает платеж через Tinkoff Касса.

    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от Tinkoff о созданном платеже
    :raises HTTPException: В случае ошибки при создании платежа
    """
    return await create_payment_gateway(tinkoff_create, amount, description)


# Создание платежей через разные платёжные системы
@router.post("/cloudpayments")
async def create_cloudpayments_payment(amount: float, description: str) -> dict:
    """
    Создает платеж через CloudPayments.

    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от CloudPayments о созданном платеже
    :raises HTTPException: В случае ошибки при создании платежа
    """
    return await create_payment_gateway(cloudpayments_create, amount, description)


# Создание платежей через разные платёжные системы
@router.post("/unitpay")
async def create_unitpay_payment(amount: float, description: str) -> dict:
    """
    Создает платеж через UnitPay.

    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от UnitPay о созданном платеже
    :raises HTTPException: В случае ошибки при создании платежа
    """
    return await create_payment_gateway(unitpay_create, amount, description)


# Создание платежей через разные платёжные системы
@router.post("/robokassa")
async def create_robokassa_payment(amount: float, description: str) -> dict:
    """
    Создает платеж через Робокассу.

    :param amount: Сумма платежа
    :param description: Описание платежа
    :return: Ответ от Робокассы о созданном платеже
    :raises HTTPException: В случае ошибки при создании платежа
    """
    return await create_payment_gateway(robokassa_create, amount, description)
