from typing import Any, Dict, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from datetime import datetime
from sqlalchemy.orm import Session
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.models.payment import PaymentStatus
from app.database import get_db
from app.utils.audit import log_audit_action
from app.utils.gateway_registry import GATEWAY_CONFIGS
from pydantic import BaseModel, ConfigDict, Field
from app.middleware.rate_limiter import limiter
from app.utils.security import get_current_user, require_any_role
from app.models.user import User
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


class PaginatedPaymentsRequest(BaseModel):
    """Запрос для получения платежей с фильтрами."""

    status: Optional[str] = None
    gateway: Optional[str] = None
    search: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class PaymentStatistics(BaseModel):
    """Статистика по платежам."""

    total_payments: int
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    total_completed_amount: float


class DashboardStats(BaseModel):
    """Расширенная статистика для дашборда."""

    total_payments: int
    total_amount: float
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    recent_payments: List[PaymentInfo]
    daily_amount: Dict[str, float]


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверка, что пользователь имеет права администратора."""
    if not current_user.has_any_role(["admin", "operator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or operator role required",
        )
    return current_user


@router.get("/statistics", response_model=PaymentStatistics)
@limiter.limit("100/minute")
async def get_statistics(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> PaymentStatistics:
    """Получение статистики по платежам."""
    stats = repository.get_statistics()
    return PaymentStatistics(**stats)


@router.get("/dashboard", response_model=DashboardStats)
@limiter.limit("50/minute")
async def get_dashboard(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent payments"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> DashboardStats:
    """Получение расширенной статистики для дашборда."""
    stats = repository.get_dashboard_stats(limit)

    return DashboardStats(
        total_payments=stats["total_payments"],
        total_amount=stats["total_amount"],
        by_status=stats["by_status"],
        by_gateway=stats["by_gateway"],
        recent_payments=[
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
            for p in stats["recent_payments"]
        ],
        daily_amount=stats["daily_amount"],
    )


@router.get("/status/{status}", response_model=PaginatedPayments)
@limiter.limit("100/minute")
async def get_payments_by_status_endpoint(
    request: Request,
    status: str,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> PaginatedPayments:
    """Получение платежей по статусу с пагинацией."""
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
    current_user: User = Depends(get_current_admin_user),
) -> PaginatedPayments:
    """Получение платежей по платёжному шлюзу с пагинацией."""
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
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Возврат платежа."""
    if not refund_request.order_id and not refund_request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    # Check current status before refunding
    existing = (
        repository.get_by_order_id(refund_request.order_id)
        if refund_request.order_id
        else repository.get_by_payment_id(refund_request.payment_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")

    status_val = existing.status.value if hasattr(existing.status, "value") else str(existing.status)
    if status_val == PaymentStatus.REFUNDED.value:
        raise HTTPException(status_code=400, detail="Payment already refunded")
    if status_val not in (PaymentStatus.COMPLETED.value, PaymentStatus.PROCESSING.value):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot refund payment in status: {status_val}",
        )

    # Call the actual payment gateway's refund API FIRST
    gateway_config = GATEWAY_CONFIGS.get(existing.payment_gateway)
    gateway_success = False
    gateway_error = None

    if gateway_config and gateway_config.get("refund_func"):
        try:
            refund_func = gateway_config["refund_func"]
            gateway_payment_id = existing.payment_id or existing.order_id
            result = await refund_func(
                payment_id=gateway_payment_id,
                amount=existing.amount,
                reason=refund_request.reason or "Refund",
            )
            gateway_success = True
            logger.info(
                f"Gateway-level refund successful for payment {existing.order_id} "
                f"via '{existing.payment_gateway}': {result}"
            )
        except Exception as e:
            gateway_error = str(e)
            logger.error(
                f"Failed to initiate gateway-level refund for payment {existing.order_id} "
                f"via '{existing.payment_gateway}': {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gateway refund failed: {gateway_error}",
            )
    else:
        logger.warning(
            f"Refund function not configured for gateway '{existing.payment_gateway}'. "
            f"Proceeding with DB-only refund for payment {existing.order_id}."
        )

    # Only update DB after gateway call succeeds
    payment = repository.update_status(
        order_id=refund_request.order_id,
        payment_id=refund_request.payment_id,
        status=PaymentStatus.REFUNDED,
        metadata={"refund_reason": refund_request.reason},
    )

    # Audit log
    log_audit_action(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="refund",
        resource_type="payment",
        resource_id=payment.order_id,
        details=f"Refund reason: {refund_request.reason or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

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
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Отмена платежа."""
    if not cancel_request.order_id and not cancel_request.payment_id:
        raise HTTPException(
            status_code=400, detail="order_id or payment_id is required"
        )

    # Check current status before canceling
    existing = (
        repository.get_by_order_id(cancel_request.order_id)
        if cancel_request.order_id
        else repository.get_by_payment_id(cancel_request.payment_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")

    status_val = existing.status.value if hasattr(existing.status, "value") else str(existing.status)
    if status_val == PaymentStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Payment already cancelled")
    if status_val in (PaymentStatus.COMPLETED.value, PaymentStatus.REFUNDED.value, PaymentStatus.FAILED.value):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel payment in status: {status_val}",
        )

    # Call the actual payment gateway's cancel API FIRST
    gateway_config = GATEWAY_CONFIGS.get(existing.payment_gateway)
    gateway_success = False
    gateway_error = None

    if gateway_config and gateway_config.get("cancel_func"):
        try:
            cancel_func = gateway_config["cancel_func"]
            gateway_payment_id = existing.payment_id or existing.order_id
            result = await cancel_func(payment_id=gateway_payment_id)
            gateway_success = True
            logger.info(
                f"Gateway-level cancellation successful for payment {existing.order_id} "
                f"via '{existing.payment_gateway}': {result}"
            )
        except Exception as e:
            gateway_error = str(e)
            logger.error(
                f"Failed to initiate gateway-level cancellation for payment {existing.order_id} "
                f"via '{existing.payment_gateway}': {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gateway cancellation failed: {gateway_error}",
            )
    else:
        logger.warning(
            f"Cancel function not configured for gateway '{existing.payment_gateway}'. "
            f"Proceeding with DB-only cancellation for payment {existing.order_id}."
        )

    # Only update DB after gateway call succeeds
    payment = repository.update_status(
        order_id=cancel_request.order_id,
        payment_id=cancel_request.payment_id,
        status=PaymentStatus.CANCELLED,
        metadata={"cancel_reason": cancel_request.reason},
    )

    # Audit log
    log_audit_action(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="cancel",
        resource_type="payment",
        resource_id=payment.order_id,
        details=f"Cancel reason: {cancel_request.reason or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

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
    current_user: User = Depends(get_current_admin_user),
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


@router.get("", response_model=PaginatedPayments)
@limiter.limit("100/minute")
async def get_all_payments(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    gateway: Optional[str] = Query(default=None, description="Filter by gateway"),
    search: Optional[str] = Query(default=None, description="Search by order_id or payment_id"),
    sort_by: str = Query(default="created_at", description="Sort by field"),
    sort_order: str = Query(default="desc", description="Sort order (asc/desc)"),
    date_from: Optional[datetime] = Query(default=None, description="Filter by date from"),
    date_to: Optional[datetime] = Query(default=None, description="Filter by date to"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> PaginatedPayments:
    """
    Получение всех платежей с пагинацией, фильтрами и сортировкой.
    
    - **page**: Номер страницы
    - **page_size**: Размер страницы (1-100)
    - **status**: Фильтр по статусу (pending, processing, completed, failed, cancelled, refunded)
    - **gateway**: Фильтр по платёжной системе
    - **search**: Поиск по order_id или payment_id
    - **sort_by**: Поле для сортировки (created_at, amount, status, payment_gateway)
    - **sort_order**: Порядок сортировки (asc, desc)
    - **date_from**: Дата начала периода
    - **date_to**: Дата конца периода
    """
    payments, total = repository.get_all_paginated(
        page=page,
        page_size=page_size,
        status=status,
        gateway=gateway,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        date_from=date_from,
        date_to=date_to,
    )
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
