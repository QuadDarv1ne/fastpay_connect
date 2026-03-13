from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status, Header, Request
from datetime import datetime
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.models.payment import PaymentStatus
from pydantic import BaseModel, ConfigDict, Field
from app.middleware.rate_limiter import limiter
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


class PaginatedPayments(BaseModel):
    """Пагинированный список платежей."""

    items: List[PaymentInfo]
    total: int
    page: int
    page_size: int
    pages: int


class PaymentStatistics(BaseModel):
    """Статистика по платежам."""

    total_payments: int
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    total_completed_amount: float


def _validate_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Валидация API ключа для admin endpoints."""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if len(x_api_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key format",
        )


@router.get("/statistics", response_model=PaymentStatistics)
@limiter.limit("100/minute")
async def get_statistics(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> PaymentStatistics:
    """Получение статистики по платежам."""
    _validate_api_key(x_api_key)
    stats = repository.get_statistics()
    return PaymentStatistics(**stats)


@router.get("/status/{status}", response_model=PaginatedPayments)
@limiter.limit("100/minute")
async def get_payments_by_status_endpoint(
    request: Request,
    status: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> PaginatedPayments:
    """Получение платежей по статусу с пагинацией."""
    _validate_api_key(x_api_key)
    payments, total = repository.get_by_status_paginated(status, page, page_size)
    pages = (total + page_size - 1) // page_size

    return PaginatedPayments(
        items=[
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
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/gateway/{gateway}", response_model=PaginatedPayments)
@limiter.limit("100/minute")
async def get_payments_by_gateway_endpoint(
    request: Request,
    gateway: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> PaginatedPayments:
    """Получение платежей по платёжному шлюзу с пагинацией."""
    _validate_api_key(x_api_key)
    payments, total = repository.get_by_gateway_paginated(gateway, page, page_size)
    pages = (total + page_size - 1) // page_size

    return PaginatedPayments(
        items=[
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
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/refund")
@limiter.limit("50/minute")
async def refund_payment(
    request: Request,
    refund_request: RefundRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Возврат платежа."""
    _validate_api_key(x_api_key)
    if not refund_request.order_id and not refund_request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = repository.update_status(
        order_id=refund_request.order_id,
        payment_id=refund_request.payment_id,
        status=PaymentStatus.REFUNDED,
        metadata={"refund_reason": refund_request.reason},
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
@limiter.limit("50/minute")
async def cancel_payment(
    request: Request,
    cancel_request: CancelRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """Отмена платежа."""
    _validate_api_key(x_api_key)
    if not cancel_request.order_id and not cancel_request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    payment = repository.update_status(
        order_id=cancel_request.order_id,
        payment_id=cancel_request.payment_id,
        status=PaymentStatus.CANCELLED,
        metadata={"cancel_reason": cancel_request.reason},
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
@limiter.limit("100/minute")
async def get_payment(
    request: Request,
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
    x_api_key: Optional[str] = Header(None),
) -> PaymentInfo:
    """Получение информации о платеже по order_id."""
    _validate_api_key(x_api_key)
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
