from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.models.payment import PaymentStatus
from pydantic import BaseModel, ConfigDict
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class RefundRequest(BaseModel):
    """Запрос на возврат платежа."""

    model_config = ConfigDict(extra="forbid")

    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    reason: Optional[str] = None


class CancelRequest(BaseModel):
    """Запрос на отмену платежа."""

    model_config = ConfigDict(extra="forbid")

    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    reason: Optional[str] = None


class PaymentInfo(BaseModel):
    """Информация о платеже."""

    model_config = ConfigDict(from_attributes=True)

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
async def get_statistics(
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentStatistics:
    """Получение статистики по платежам."""
    stats = repository.get_statistics()
    return PaymentStatistics(**stats)


@router.get("/status/{status}", response_model=List[PaymentInfo])
async def get_payments_by_status_endpoint(
    status: str,
    limit: int = Query(default=100, ge=1, le=1000),
    repository: PaymentRepository = Depends(get_payment_repository),
) -> List[PaymentInfo]:
    """Получение платежей по статусу."""
    payments = repository.get_by_status(status, limit)
    return [
        PaymentInfo(
            order_id=p.order_id,
            payment_id=p.payment_id,
            payment_gateway=p.payment_gateway,
            amount=p.amount,
            currency=p.currency,
            status=p.status.value if isinstance(p.status, PaymentStatus) else p.status,
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
    repository: PaymentRepository = Depends(get_payment_repository),
) -> List[PaymentInfo]:
    """Получение платежей по платёжному шлюзу."""
    payments = repository.get_by_gateway(gateway, limit)
    return [
        PaymentInfo(
            order_id=p.order_id,
            payment_id=p.payment_id,
            payment_gateway=p.payment_gateway,
            amount=p.amount,
            currency=p.currency,
            status=p.status.value if isinstance(p.status, PaymentStatus) else p.status,
            description=p.description,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in payments
    ]


@router.post("/refund")
async def refund_payment(
    request: RefundRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Возврат платежа."""
    if not request.order_id and not request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = repository.update_status(
        order_id=request.order_id,
        payment_id=request.payment_id,
        status=PaymentStatus.REFUNDED,
        metadata={"refund_reason": request.reason},
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "status": "success",
        "message": "Payment refunded",
        "order_id": payment.order_id,
        "new_status": payment.status.value if isinstance(payment.status, PaymentStatus) else payment.status,
    }


@router.post("/cancel")
async def cancel_payment(
    request: CancelRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Отмена платежа."""
    if not request.order_id and not request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = repository.update_status(
        order_id=request.order_id,
        payment_id=request.payment_id,
        status=PaymentStatus.CANCELLED,
        metadata={"cancel_reason": request.reason},
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "status": "success",
        "message": "Payment cancelled",
        "order_id": payment.order_id,
        "new_status": payment.status.value if isinstance(payment.status, PaymentStatus) else payment.status,
    }


@router.get("/{order_id}", response_model=PaymentInfo)
async def get_payment(
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentInfo:
    """Получение информации о платеже по order_id."""
    payment = repository.get_by_order_id(order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return PaymentInfo(
        order_id=payment.order_id,
        payment_id=payment.payment_id,
        payment_gateway=payment.payment_gateway,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status.value if isinstance(payment.status, PaymentStatus) else payment.status,
        description=payment.description,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )
