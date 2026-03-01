from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.services.payment_service import (
    get_payment_by_order_id,
    get_payment_by_id,
    get_payments_by_status,
    get_payments_by_gateway,
    refund_payment,
    cancel_payment,
    get_payment_statistics,
)
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class RefundRequest(BaseModel):
    """Запрос на возврат платежа."""

    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    reason: Optional[str] = None


class CancelRequest(BaseModel):
    """Запрос на отмену платежа."""

    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    reason: Optional[str] = None


class PaymentInfo(BaseModel):
    """Информация о платеже."""

    order_id: str
    payment_id: Optional[str]
    payment_gateway: str
    amount: float
    currency: str
    status: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class PaymentStatistics(BaseModel):
    """Статистика по платежам."""

    total_payments: int
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    total_completed_amount: float


@router.get("/statistics", response_model=PaymentStatistics)
async def statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Получение статистики по платежам."""
    stats = get_payment_statistics(db)
    return stats


@router.get("/status/{status}", response_model=List[PaymentInfo])
async def get_payments_by_status_endpoint(
    status: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[PaymentInfo]:
    """Получение платежей по статусу."""
    payments = get_payments_by_status(db, status, limit)
    return [
        PaymentInfo(
            order_id=p.order_id,
            payment_id=p.payment_id,
            payment_gateway=p.payment_gateway,
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in payments
    ]


@router.get("/gateway/{gateway}", response_model=List[PaymentInfo])
async def get_payments_by_gateway_endpoint(
    gateway: str,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> List[PaymentInfo]:
    """Получение платежей по платёжному шлюзу."""
    payments = get_payments_by_gateway(db, gateway, limit)
    return [
        PaymentInfo(
            order_id=p.order_id,
            payment_id=p.payment_id,
            payment_gateway=p.payment_gateway,
            amount=p.amount,
            currency=p.currency,
            status=p.status,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in payments
    ]


@router.post("/refund")
async def refund(
    request: RefundRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Возврат платежа."""
    if not request.order_id and not request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = refund_payment(
        db,
        order_id=request.order_id,
        payment_id=request.payment_id,
        reason=request.reason,
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "status": "success",
        "message": "Payment refunded",
        "order_id": payment.order_id,
        "new_status": payment.status,
    }


@router.post("/cancel")
async def cancel(
    request: CancelRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Отмена платежа."""
    if not request.order_id and not request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = cancel_payment(
        db,
        order_id=request.order_id,
        payment_id=request.payment_id,
        reason=request.reason,
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "status": "success",
        "message": "Payment cancelled",
        "order_id": payment.order_id,
        "new_status": payment.status,
    }


@router.get("/{order_id}", response_model=PaymentInfo)
async def get_payment(order_id: str, db: Session = Depends(get_db)) -> PaymentInfo:
    """Получение информации о платеже по order_id."""
    payment = get_payment_by_order_id(db, order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentInfo(
        order_id=payment.order_id,
        payment_id=payment.payment_id,
        payment_gateway=payment.payment_gateway,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        description=payment.description,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )
