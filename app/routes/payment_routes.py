from typing import Any, Callable, Dict
from fastapi import APIRouter, HTTPException, Depends, Request
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
from app.schemas import PaymentRequest, PaymentResponse
from app.database import get_db
from app.services.payment_service import create_payment_record
from app.middleware.rate_limiter import limiter
from sqlalchemy.orm import Session
import asyncio
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_order_id() -> str:
    """Генерация уникального order_id."""
    return str(uuid.uuid4()).replace("-", "")[:12]


async def create_payment_gateway(
    payment_function: Callable,
    amount: float,
    description: str,
    order_id: str,
) -> Dict[str, Any]:
    """Асинхронный вызов платёжного шлюза."""
    try:
        return await asyncio.to_thread(payment_function, amount, description, order_id)
    except Exception as e:
        logger.error(f"Payment gateway error: {e}")
        raise HTTPException(status_code=400, detail=f"Payment gateway error: {e}")


@router.post("/yookassa", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def create_yookassa_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Платёж через YooKassa."""
    order_id = payment_request.order_id or generate_order_id()

    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="yookassa",
        amount=payment_request.amount,
        description=payment_request.description,
    )

    result = await create_payment_gateway(
        yookassa_create, payment_request.amount, payment_request.description, order_id
    )

    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        db.commit()
        raise HTTPException(status_code=400, detail=result["error"])

    db_payment.payment_id = result.get("id")
    db_payment.payment_url = result.get("confirmation", {}).get("confirmation_url")
    db_payment.status = "processing"
    db.commit()

    return PaymentResponse(
        success=True,
        payment_id=db_payment.payment_id,
        payment_url=db_payment.payment_url,
        order_id=order_id,
        amount=payment_request.amount,
        message="Платёж успешно создан",
    )


@router.post("/tinkoff", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def create_tinkoff_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Платёж через Tinkoff."""
    order_id = payment_request.order_id or generate_order_id()

    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="tinkoff",
        amount=payment_request.amount,
        description=payment_request.description,
    )

    result = await create_payment_gateway(
        tinkoff_create, payment_request.amount, payment_request.description, order_id
    )

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
        amount=payment_request.amount,
        message="Платёж успешно создан",
    )


@router.post("/cloudpayments", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def create_cloudpayments_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Платёж через CloudPayments."""
    order_id = payment_request.order_id or generate_order_id()

    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="cloudpayments",
        amount=payment_request.amount,
        description=payment_request.description,
    )

    result = await create_payment_gateway(
        cloudpayments_create, payment_request.amount, payment_request.description, order_id
    )

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
        amount=payment_request.amount,
        message="Платёж успешно создан",
    )


@router.post("/unitpay", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def create_unitpay_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Платёж через UnitPay."""
    order_id = payment_request.order_id or generate_order_id()

    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="unitpay",
        amount=payment_request.amount,
        description=payment_request.description,
    )

    result = await create_payment_gateway(
        unitpay_create, payment_request.amount, payment_request.description, order_id
    )

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
        amount=payment_request.amount,
        message="Платёж успешно создан",
    )


@router.post("/robokassa", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def create_robokassa_payment(
    request: Request,
    payment_request: PaymentRequest,
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Платёж через Robokassa."""
    order_id = payment_request.order_id or generate_order_id()

    db_payment = create_payment_record(
        db=db,
        order_id=order_id,
        payment_gateway="robokassa",
        amount=payment_request.amount,
        description=payment_request.description,
    )

    result = await create_payment_gateway(
        robokassa_create, payment_request.amount, payment_request.description, order_id
    )

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
        amount=payment_request.amount,
        message="Платёж успешно создан",
    )
