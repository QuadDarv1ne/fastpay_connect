"""
Webhook management API routes.

Endpoints для управления webhook событиями:
- Список событий с фильтрами и пагинацией
- Детали события
- Повторная отправка (retry)
- Статистика
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.utils.security import get_current_user
from app.models.user import User
from app.middleware.rate_limiter import limiter
from app.schemas.webhook import (
    WebhookEventResponse,
    WebhookEventListResponse,
    WebhookStatsResponse,
    WebhookRetryRequest,
)

router = APIRouter()


def get_repository(db: Any = Depends(get_db)) -> WebhookEventRepository:
    """Dependency для получения WebhookEventRepository."""
    return WebhookEventRepository(db)


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверка прав администратора."""
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required to manage webhooks",
        )
    return current_user


@router.get(
    "/events",
    response_model=WebhookEventListResponse,
    tags=["Webhook Management"],
)
@limiter.limit("30/minute")
async def list_webhook_events(
    request: Any,
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(20, ge=1, le=100, description="Размер страницы"),
    gateway: Optional[str] = Query(None, description="Фильтр по платёжной системе"),
    status_filter: Optional[str] = Query(None, alias="status", description="Фильтр по статусу"),
    order_id: Optional[str] = Query(None, description="Фильтр по ID заказа"),
    event_id: Optional[str] = Query(None, description="Фильтр по ID события"),
    days: int = Query(7, ge=1, le=90, description="Период в днях"),
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> WebhookEventListResponse:
    """
    Получить список webhook событий с фильтрами и пагинацией.
    
    - **page**: Номер страницы (начиная с 1)
    - **page_size**: Количество элементов на странице (1-100)
    - **gateway**: Фильтр по платёжной системе (yookassa, tinkoff, etc.)
    - **status**: Фильтр по статусу (pending, processing, success, retry, failed)
    - **order_id**: Фильтр по ID заказа
    - **event_id**: Фильтр по ID события
    - **days**: Период выборки в днях (1-90)
    """
    # Получаем события с пагинацией
    events, total = repository.get_paginated(
        page=page,
        page_size=page_size,
        gateway=gateway,
        status=status_filter,
    )
    
    # Применяем дополнительные фильтры
    if order_id:
        events = [e for e in events if e.order_id == order_id]
        total = len(events)
    
    if event_id:
        events = [e for e in events if e.event_id == event_id]
        total = len(events)
    
    # Фильтр по периоду
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = [e for e in events if e.created_at >= cutoff]
    total = len(events)
    
    return WebhookEventListResponse(
        events=[event.to_dict() for event in events],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=WebhookEventResponse,
    tags=["Webhook Management"],
)
@limiter.limit("60/minute")
async def get_webhook_event(
    request: Any,
    event_id: str,
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> WebhookEventResponse:
    """
    Получить детали webhook события по ID.
    """
    event = repository.get_by_event_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook event {event_id} not found",
        )
    
    return WebhookEventResponse(**event.to_dict())


@router.post(
    "/events/{event_id}/retry",
    response_model=WebhookEventResponse,
    tags=["Webhook Management"],
)
@limiter.limit("10/minute")
async def retry_webhook_event(
    request: Any,
    event_id: str,
    retry_data: Optional[WebhookRetryRequest] = None,
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> WebhookEventResponse:
    """
    Повторная отправка webhook события.
    
    Событие должно быть в статусе failed или success.
    """
    event = repository.get_by_event_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook event {event_id} not found",
        )
    
    # Проверка статуса
    if event.status not in [WebhookEventStatus.FAILED, WebhookEventStatus.SUCCESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot retry event in {event.status.value} status. Only failed or success events can be retried.",
        )
    
    # Сброс события для повторной обработки
    event.retry_count = 0
    event.status = WebhookEventStatus.PENDING
    event.last_error = None
    event.next_retry_at = None
    event.updated_at = datetime.now(timezone.utc)
    
    try:
        repository.db.commit()
        repository.db.refresh(event)
    except Exception as e:
        repository.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset event: {str(e)}",
        )
    
    # NOTE: Re-dispatching via Celery is intentionally disabled here.
    # The existing `process_webhook_task` expects (gateway, payload, auth_value)
    # rather than an event_id. A dedicated retry-dispatch task should be
    # created when Celery-based reprocessing is needed.
    
    return WebhookEventResponse(**event.to_dict())


@router.get(
    "/stats",
    response_model=WebhookStatsResponse,
    tags=["Webhook Management"],
)
@limiter.limit("30/minute")
async def get_webhook_stats(
    request: Any,
    days: int = Query(7, ge=1, le=90, description="Период в днях"),
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> WebhookStatsResponse:
    """
    Получить статистику webhook событий.
    """
    stats = repository.get_statistics(days=days)
    
    return WebhookStatsResponse(
        total=stats["total"],
        by_status=stats["by_status"],
        by_gateway=stats["by_gateway"],
        retrying=stats["retrying"],
        failed=stats["failed"],
        period_days=stats["period_days"],
    )


@router.get(
    "/dashboard",
    tags=["Webhook Management"],
)
@limiter.limit("30/minute")
async def get_webhook_dashboard(
    request: Any,
    limit: int = Query(10, ge=1, le=100, description="Количество последних событий"),
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить расширенную статистику для дашборда.
    """
    return repository.get_dashboard_stats(limit=limit)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Webhook Management"],
)
@limiter.limit("10/minute")
async def delete_webhook_event(
    request: Any,
    event_id: str,
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
):
    """
    Удалить webhook событие.
    
    Можно удалять только события в статусе success или failed.
    """
    event = repository.get_by_event_id(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook event {event_id} not found",
        )
    
    # Проверка статуса
    if event.status not in [WebhookEventStatus.SUCCESS, WebhookEventStatus.FAILED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete event in {event.status.value} status. Only success or failed events can be deleted.",
        )
    
    try:
        repository.db.delete(event)
        repository.db.commit()
    except Exception as e:
        repository.db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete event: {str(e)}",
        )
    
    return None


@router.post(
    "/cleanup",
    tags=["Webhook Management"],
)
@limiter.limit("5/minute")
async def cleanup_old_events(
    request: Any,
    days: int = Query(30, ge=7, le=365, description="Удалить события старше N дней"),
    repository: WebhookEventRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, int]:
    """
    Очистка старых webhook событий.
    
    Удаляет события в статусе success или failed старше указанного периода.
    """
    deleted = repository.cleanup_old_events(days=days)
    
    return {"deleted": deleted, "days": days}
