"""
Webhook monitoring routes для dashboard.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.repositories.webhook_event_repository import WebhookEventRepository
from app.utils.security import get_current_user, require_any_role
from app.models.user import User
from app.middleware.rate_limiter import limiter

router = APIRouter()


def get_webhook_repository(db: Any = Depends(get_db)) -> WebhookEventRepository:
    """Dependency для получения WebhookEventRepository."""
    return WebhookEventRepository(db)


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверка прав администратора."""
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=403,
            detail="Admin role required",
        )
    return current_user


@router.get("/dashboard-ui", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def webhook_dashboard_ui(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
) -> HTMLResponse:
    """
    UI дашборд для мониторинга webhook событий.
    """
    from pathlib import Path
    from fastapi.templating import Jinja2Templates
    
    templates_dir = Path(__file__).parent.parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    return templates.TemplateResponse(
        "webhook_dashboard.html",
        {"request": request}
    )


@router.get("/overview")
@limiter.limit("30/minute")
async def get_webhook_overview(
    request: Request,
    days: int = Query(default=7, ge=1, le=30, description="Period in days"),
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить общую статистику webhook событий.
    
    - **days**: Период в днях (1-30)
    """
    stats = repository.get_statistics(days=days)
    return {
        "status": "success",
        "data": stats,
    }


@router.get("/dashboard")
@limiter.limit("30/minute")
async def get_webhook_dashboard(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50, description="Number of recent events"),
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить расширенную статистику для дашборда.
    
    - **limit**: Количество последних событий (1-50)
    """
    stats = repository.get_dashboard_stats(limit=limit)
    return {
        "status": "success",
        "data": stats,
    }


@router.get("/events")
@limiter.limit("100/minute")
async def get_webhook_events(
    request: Request,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    gateway: Optional[str] = Query(default=None, description="Filter by gateway"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить список webhook событий с пагинацией.
    
    - **page**: Номер страницы
    - **page_size**: Количество элементов на странице (1-100)
    - **gateway**: Фильтр по платёжной системе
    - **status**: Фильтр по статусу
    """
    events, total = repository.get_paginated(page, page_size, gateway, status)
    pages = (total + page_size - 1) // page_size
    
    return {
        "status": "success",
        "data": {
            "items": [event.to_dict() for event in events],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        },
    }


@router.get("/events/{event_id}")
@limiter.limit("100/minute")
async def get_webhook_event(
    request: Request,
    event_id: str,
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить информацию о webhook событии.
    """
    event = repository.get_by_event_id(event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    return {
        "status": "success",
        "data": event.to_dict(),
    }


@router.get("/events/order/{order_id}")
@limiter.limit("100/minute")
async def get_webhook_events_for_order(
    request: Request,
    order_id: str,
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить все webhook события для заказа.
    """
    events = repository.get_by_order_id(order_id)
    
    return {
        "status": "success",
        "data": [event.to_dict() for event in events],
    }


@router.get("/retry-queue")
@limiter.limit("30/minute")
async def get_retry_queue(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить события, ожидающие повторной обработки.
    """
    events = repository.get_events_for_retry(limit=limit)
    
    return {
        "status": "success",
        "data": {
            "count": len(events),
            "items": [event.to_dict() for event in events],
        },
    }


@router.post("/cleanup")
@limiter.limit("10/hour")
async def cleanup_old_events(
    request: Request,
    days: int = Query(default=30, ge=7, le=365, description="Delete events older than N days"),
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Очистить старые webhook события.
    
    - **days**: Удалить события старше N дней (7-365)
    """
    deleted = repository.cleanup_old_events(days=days)
    
    return {
        "status": "success",
        "message": f"Deleted {deleted} old webhook events",
        "deleted_count": deleted,
    }


@router.get("/metrics")
@limiter.limit("30/minute")
async def get_webhook_metrics(
    request: Request,
    repository: WebhookEventRepository = Depends(get_webhook_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить метрики для Prometheus.
    """
    stats = repository.get_statistics(days=1)
    
    return {
        "status": "success",
        "data": {
            "total_webhooks_24h": stats["total"],
            "by_gateway": stats["by_gateway"],
            "by_status": stats["by_status"],
            "retrying": stats["retrying"],
            "failed": stats["failed"],
        },
    }
