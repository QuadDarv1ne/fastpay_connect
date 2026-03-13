"""Admin routes for API v1."""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any, List, Optional

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter
from app.utils.security import get_current_user, require_any_role
from app.models.user import User
from app.models.payment import PaymentStatus

router = APIRouter()


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверка прав администратора."""
    if not current_user.has_any_role(["admin", "operator"]):
        raise HTTPException(
            status_code=403,
            detail="Admin or operator role required",
        )
    return current_user


@router.get("/payments/statistics")
@limiter.limit("100/minute")
async def get_statistics_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Get payment statistics (v1)."""
    stats = repository.get_statistics()
    return stats


@router.get("/payments/dashboard")
@limiter.limit("50/minute")
async def get_dashboard_v1(
    request: Request,
    limit: int = 10,
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Get dashboard statistics (v1)."""
    stats = repository.get_dashboard_stats(limit)
    return stats


@router.get("/payments/{order_id}")
@limiter.limit("100/minute")
async def get_payment_v1(
    request: Request,
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Get payment by order_id (v1)."""
    payment = repository.get_by_order_id(order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "order_id": payment.order_id,
        "payment_id": payment.payment_id,
        "payment_gateway": payment.payment_gateway,
        "amount": payment.amount,
        "currency": payment.currency,
        "status": payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
        "description": payment.description,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
    }


@router.post("/payments/refund")
@limiter.limit("50/minute")
async def refund_payment_v1(
    request: Request,
    refund_data: Dict[str, Any],
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Refund a payment (v1)."""
    order_id = refund_data.get("order_id")
    payment_id = refund_data.get("payment_id")
    reason = refund_data.get("reason")
    
    if not order_id and not payment_id:
        raise HTTPException(status_code=400, detail="order_id or payment_id required")
    
    payment = repository.update_status(
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentStatus.REFUNDED,
        metadata={"refund_reason": reason},
    )
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "status": "success",
        "message": "Payment refunded",
        "order_id": payment.order_id,
    }


@router.post("/payments/cancel")
@limiter.limit("50/minute")
async def cancel_payment_v1(
    request: Request,
    cancel_data: Dict[str, Any],
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """Cancel a payment (v1)."""
    order_id = cancel_data.get("order_id")
    payment_id = cancel_data.get("payment_id")
    reason = cancel_data.get("reason")
    
    if not order_id and not payment_id:
        raise HTTPException(status_code=400, detail="order_id or payment_id required")
    
    payment = repository.update_status(
        order_id=order_id,
        payment_id=payment_id,
        status=PaymentStatus.CANCELLED,
        metadata={"cancel_reason": reason},
    )
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    return {
        "status": "success",
        "message": "Payment cancelled",
        "order_id": payment.order_id,
    }
