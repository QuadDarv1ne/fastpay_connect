from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
from app.schemas import PaymentRequest, PaymentResponse
from app.database import get_db
from app.services.payment_service import create_payment_record, update_payment_status
from sqlalchemy.orm import Session
import asyncio
import uuid
import json

router = APIRouter()


def generate_order_id() -> str:
    """Генерирует уникальный идентификатор заказа."""
    return str(uuid.uuid4()).replace("-", "")[:12]


async def create_payment_gateway(payment_function, amount: float, description: str, order_id: str) -> dict:
    """
    Асинхронно создает платеж через переданную платёжную систему.
    """
    try:
        return await asyncio.to_thread(payment_function, amount, description, order_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error in payment gateway: {str(e)}")


@router.post("/yookassa", response_model=PaymentResponse)
async def create_yookassa_payment(request: PaymentRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Создает платеж через YooKassa."""
    order_id = request.order_id or generate_order_id()
    
    # Создаём запись в БД
    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="yookassa",
        amount=request.amount,
        description=request.description,
    )
    
    result = await create_payment_gateway(yookassa_create, request.amount, request.description, order_id)
    
    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])
    
    # Обновляем запись с данными от шлюза
    db_payment.payment_id = result.get("id")
    db_payment.payment_url = result.get("confirmation", {}).get("confirmation_url")
    db_payment.status = "processing"
    db.commit()
    
    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        payment_url=db_payment.payment_url,
        order_id=order_id,
        amount=request.amount,
        message="Платёж успешно создан"
    )


@router.post("/tinkoff", response_model=PaymentResponse)
async def create_tinkoff_payment(request: PaymentRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Создает платеж через Tinkoff."""
    order_id = request.order_id or generate_order_id()
    
    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="tinkoff",
        amount=request.amount,
        description=request.description,
    )
    
    result = await create_payment_gateway(tinkoff_create, request.amount, request.description, order_id)
    
    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])
    
    db_payment.payment_id = result.get("payment_id")
    db_payment.payment_url = result.get("payment_url")
    db_payment.status = "processing"
    db.commit()
    
    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        payment_url=db_payment.payment_url,
        order_id=order_id,
        amount=request.amount,
        message="Платёж успешно создан"
    )


@router.post("/cloudpayments", response_model=PaymentResponse)
async def create_cloudpayments_payment(request: PaymentRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Создает платеж через CloudPayments."""
    order_id = request.order_id or generate_order_id()
    
    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="cloudpayments",
        amount=request.amount,
        description=request.description,
    )
    
    result = await create_payment_gateway(cloudpayments_create, request.amount, request.description, order_id)
    
    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])
    
    db_payment.payment_id = result.get("transaction_id")
    db_payment.status = "processing"
    db.commit()
    
    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        order_id=order_id,
        amount=request.amount,
        message="Платёж успешно создан"
    )


@router.post("/unitpay", response_model=PaymentResponse)
async def create_unitpay_payment(request: PaymentRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Создает платеж через UnitPay."""
    order_id = request.order_id or generate_order_id()
    
    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="unitpay",
        amount=request.amount,
        description=request.description,
    )
    
    result = await create_payment_gateway(unitpay_create, request.amount, request.description, order_id)
    
    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])
    
    db_payment.payment_id = result.get("payment_id")
    db_payment.status = "processing"
    db.commit()
    
    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        order_id=order_id,
        amount=request.amount,
        message="Платёж успешно создан"
    )


@router.post("/robokassa", response_model=PaymentResponse)
async def create_robokassa_payment(request: PaymentRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Создает платеж через Робокассу."""
    order_id = request.order_id or generate_order_id()
    
    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="robokassa",
        amount=request.amount,
        description=request.description,
    )
    
    result = await create_payment_gateway(robokassa_create, request.amount, request.description, order_id)
    
    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])
    
    db_payment.payment_id = result.get("invoice_id")
    db_payment.status = "processing"
    db.commit()
    
    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        order_id=order_id,
        amount=request.amount,
        message="Платёж успешно создан"
    )
