"""Admin routes for API v2.

Improvements over v1:
- Proper Pydantic v2 typed response models
- Audit log access endpoint
- Structured error responses
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.database import get_db
from app.models.payment import PaymentStatus
from app.schemas.v2 import (
    AdminPaymentInfo,
    AdminStatisticsResponse,
    AdminActionResponse,
    AuditLogEntry,
    PaginatedAuditLogs,
    PaymentStatusEnum,
)
from app.middleware.rate_limiter import limiter
from app.utils.security import get_current_user
from app.utils.audit import log_audit_action
from app.models.user import User
from app.models.audit_log import AuditLog

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Check admin/operator role."""
    if not current_user.has_any_role(["admin", "operator"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or operator role required",
        )
    return current_user


@router.get("/statistics", response_model=AdminStatisticsResponse)
@limiter.limit("100/minute")
async def get_statistics_v2(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> AdminStatisticsResponse:
    """Get payment statistics (v2)."""
    stats = repository.get_statistics()
    return AdminStatisticsResponse(**stats)


@router.post("/refund", response_model=AdminActionResponse)
@limiter.limit("50/minute")
async def refund_payment_v2(
    request: Request,
    refund_data: Dict[str, Any],
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    """Refund a payment (v2)."""
    order_id = refund_data.get("order_id")
    payment_id = refund_data.get("payment_id")
    reason = refund_data.get("reason")

    if not order_id and not payment_id:
        raise HTTPException(status_code=400, detail="order_id or payment_id required")

    existing = repository.get_by_order_id(order_id) if order_id else repository.get_by_payment_id(payment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")

    status_val = existing.status.value if hasattr(existing.status, "value") else str(existing.status)
    if status_val == PaymentStatus.REFUNDED.value:
        raise HTTPException(status_code=400, detail="Payment already refunded")
    if status_val not in (PaymentStatus.COMPLETED.value, PaymentStatus.PROCESSING.value):
        raise HTTPException(status_code=400, detail=f"Cannot refund payment in status: {status_val}")

    payment = repository.update_status(
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentStatus.REFUNDED,
        metadata={"refund_reason": reason},
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    log_audit_action(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="refund",
        resource_type="payment",
        resource_id=payment.order_id,
        details=f"Refund reason: {reason or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

    new_status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    return AdminActionResponse(
        status="success",
        message="Payment refunded",
        order_id=payment.order_id,
        new_status=PaymentStatusEnum(new_status),
    )


@router.post("/cancel", response_model=AdminActionResponse)
@limiter.limit("50/minute")
async def cancel_payment_v2(
    request: Request,
    cancel_data: Dict[str, Any],
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
) -> AdminActionResponse:
    """Cancel a payment (v2)."""
    order_id = cancel_data.get("order_id")
    payment_id = cancel_data.get("payment_id")
    reason = cancel_data.get("reason")

    if not order_id and not payment_id:
        raise HTTPException(status_code=400, detail="order_id or payment_id required")

    existing = repository.get_by_order_id(order_id) if order_id else repository.get_by_payment_id(payment_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Payment not found")

    status_val = existing.status.value if hasattr(existing.status, "value") else str(existing.status)
    if status_val == PaymentStatus.CANCELLED.value:
        raise HTTPException(status_code=400, detail="Payment already cancelled")
    if status_val in (PaymentStatus.COMPLETED.value, PaymentStatus.REFUNDED.value, PaymentStatus.FAILED.value):
        raise HTTPException(status_code=400, detail=f"Cannot cancel payment in status: {status_val}")

    payment = repository.update_status(
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentStatus.CANCELLED,
        metadata={"cancel_reason": reason},
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    log_audit_action(
        db=db,
        user_id=current_user.id,
        username=current_user.username,
        action="cancel",
        resource_type="payment",
        resource_id=payment.order_id,
        details=f"Cancel reason: {reason or 'N/A'}",
        ip_address=request.client.host if request.client else None,
    )

    new_status = payment.status.value if hasattr(payment.status, "value") else str(payment.status)
    return AdminActionResponse(
        status="success",
        message="Payment cancelled",
        order_id=payment.order_id,
        new_status=PaymentStatusEnum(new_status),
    )


@router.get("/audit-logs", response_model=PaginatedAuditLogs)
@limiter.limit("100/minute")
async def get_audit_logs_v2(
    request: Request,
    page: int = Query(default=1, ge=1, le=1000),
    page_size: int = Query(default=20, ge=1, le=100),
    action: Optional[str] = Query(default=None, description="Filter by action (refund, cancel, etc.)"),
    user_id: Optional[int] = Query(default=None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> PaginatedAuditLogs:
    """Get audit log entries (v2)."""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return PaginatedAuditLogs(
        items=[
            AuditLogEntry(
                id=log.id,
                user_id=log.user_id,
                username=log.username,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                details=log.details,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
