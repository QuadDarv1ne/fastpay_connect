"""Subscription routes for recurring payments."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.user import User
from app.schemas.subscription import (SubscriptionActionResponse,
                                      SubscriptionCancelRequest,
                                      SubscriptionCreateRequest,
                                      SubscriptionListResponse,
                                      SubscriptionResponse,
                                      SubscriptionStatusEnum)
from app.services.subscription_service import (SubscriptionService,
                                               SubscriptionServiceError)
from app.utils.security import get_current_user

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


def get_subscription_service(db: Session = Depends(get_db)) -> SubscriptionService:
    """Dependency for SubscriptionService."""
    return SubscriptionService(db)


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")
    return current_user


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("50/hour")
async def create_subscription(
    request: Request,
    sub_data: SubscriptionCreateRequest,
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """Create a new recurring payment subscription."""
    try:
        sub = service.create_subscription(user_id=current_user.id, request=sub_data)
    except SubscriptionServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return SubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        plan_id=sub.plan_id,
        plan_name=sub.plan_name,
        amount=float(sub.amount),
        currency=sub.currency,
        interval=sub.interval,
        status=SubscriptionStatusEnum(sub.status),
        payment_gateway=sub.payment_gateway,
        trial_end=sub.trial_end,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        next_billing_date=sub.next_billing_date,
        cancel_at_period_end=bool(sub.cancel_at_period_end),
        created_at=sub.created_at,
    )


@router.get("", response_model=SubscriptionListResponse)
@limiter.limit("100/hour")
async def list_subscriptions(
    request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionListResponse:
    """List user's subscriptions."""
    offset = (page - 1) * page_size
    subs = service.get_user_subscriptions(
        user_id=current_user.id, offset=offset, limit=page_size
    )
    total = service.count_user_subscriptions(user_id=current_user.id)
    pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return SubscriptionListResponse(
        items=[
            SubscriptionResponse(
                id=s.id,
                user_id=s.user_id,
                plan_id=s.plan_id,
                plan_name=s.plan_name,
                amount=float(s.amount),
                currency=s.currency,
                interval=s.interval,
                status=SubscriptionStatusEnum(s.status),
                payment_gateway=s.payment_gateway,
                trial_end=s.trial_end,
                current_period_start=s.current_period_start,
                current_period_end=s.current_period_end,
                next_billing_date=s.next_billing_date,
                cancel_at_period_end=bool(s.cancel_at_period_end),
                created_at=s.created_at,
            )
            for s in subs
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
@limiter.limit("100/hour")
async def get_subscription(
    request: Request,
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    """Get subscription details."""
    sub = service.get_subscription(subscription_id)
    if not sub or sub.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        plan_id=sub.plan_id,
        plan_name=sub.plan_name,
        amount=float(sub.amount),
        currency=sub.currency,
        interval=sub.interval,
        status=SubscriptionStatusEnum(sub.status),
        payment_gateway=sub.payment_gateway,
        trial_end=sub.trial_end,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        next_billing_date=sub.next_billing_date,
        cancel_at_period_end=bool(sub.cancel_at_period_end),
        created_at=sub.created_at,
    )


@router.post("/{subscription_id}/cancel", response_model=SubscriptionActionResponse)
@limiter.limit("20/hour")
async def cancel_subscription(
    request: Request,
    subscription_id: int,
    cancel_data: SubscriptionCancelRequest,
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionActionResponse:
    """Cancel a subscription."""
    try:
        sub = service.cancel_subscription(
            subscription_id=subscription_id,
            user_id=current_user.id,
            reason=cancel_data.reason,
            cancel_at_period_end=cancel_data.cancel_at_period_end,
        )
    except SubscriptionServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionActionResponse(
        success=True,
        subscription_id=sub.id,
        status=SubscriptionStatusEnum(sub.status),
        message="Subscription cancelled",
    )


@router.post("/{subscription_id}/pause", response_model=SubscriptionActionResponse)
@limiter.limit("20/hour")
async def pause_subscription(
    request: Request,
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionActionResponse:
    """Pause a subscription."""
    try:
        sub = service.pause_subscription(subscription_id, current_user.id)
    except SubscriptionServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionActionResponse(
        success=True,
        subscription_id=sub.id,
        status=SubscriptionStatusEnum(sub.status),
        message="Subscription paused",
    )


@router.post("/{subscription_id}/resume", response_model=SubscriptionActionResponse)
@limiter.limit("20/hour")
async def resume_subscription(
    request: Request,
    subscription_id: int,
    current_user: User = Depends(get_current_active_user),
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionActionResponse:
    """Resume a paused subscription."""
    try:
        sub = service.resume_subscription(subscription_id, current_user.id)
    except SubscriptionServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return SubscriptionActionResponse(
        success=True,
        subscription_id=sub.id,
        status=SubscriptionStatusEnum(sub.status),
        message="Subscription resumed",
    )
