"""Payment Analytics API routes.

Endpoints для аналитики платежей:
- Общая статистика
- Аналитика за период
- Динамика по дням/неделям/месяцам
- Отчёты по шлюзам и валютам
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.utils.security import get_current_user

router = APIRouter()


def get_repository(db: Any = Depends(get_db)) -> PaymentRepository:
    """Dependency для получения PaymentRepository."""
    return PaymentRepository(db)


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверка прав администратора."""
    if not current_user.has_role("admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required for analytics",
        )
    return current_user


@router.get(
    "/analytics/summary",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_payment_analytics_summary(
    request: Any,
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    gateway: Optional[str] = Query(None, description="Фильтр по шлюзу"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить сводную аналитику платежей.

    - **days**: Период в днях (1-365)
    - **gateway**: Фильтр по платёжной системе
    - **tenant_id**: Фильтр по tenant ID
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    return repository.get_analytics(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
        gateway=gateway,
    )


@router.get(
    "/analytics/period",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_payment_analytics_period(
    request: Any,
    start_date: str = Query(..., description="Начальная дата (ISO 8601)"),
    end_date: str = Query(..., description="Конечная дата (ISO 8601)"),
    gateway: Optional[str] = Query(None, description="Фильтр по шлюзу"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить аналитику за произвольный период.

    - **start_date**: Начальная дата (ISO 8601)
    - **end_date**: Конечная дата (ISO 8601)
    - **gateway**: Фильтр по платёжной системе
    - **tenant_id**: Фильтр по tenant ID
    """
    try:
        start = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}. Use ISO 8601",
        )

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )

    return repository.get_analytics(
        start_date=start,
        end_date=end,
        tenant_id=tenant_id,
        gateway=gateway,
    )


@router.get(
    "/analytics/gateways",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_gateway_analytics(
    request: Any,
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить аналитику по платёжным шлюзам.

    Возвращает статистику по каждому шлюзу:
    - Количество транзакций
    - Сумма
    - Распределение по статусам
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = repository.get_analytics(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
    )

    # Формируем детальную статистику по шлюзам
    gateway_stats = {}
    for gateway, count in analytics.get("by_gateway", {}).items():
        gateway_stats[gateway] = {
            "transactions": count,
            "percentage": round(count / max(analytics["summary"]["total_transactions"], 1) * 100, 2),
        }

    return {
        "period": analytics["period"],
        "total_transactions": analytics["summary"]["total_transactions"],
        "gateways": gateway_stats,
    }


@router.get(
    "/analytics/currencies",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_currency_analytics(
    request: Any,
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить аналитику по валютам.

    Возвращает суммы транзакций по каждой валюте.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = repository.get_analytics(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
    )

    return {
        "period": analytics["period"],
        "currencies": analytics.get("by_currency", {}),
    }


@router.get(
    "/analytics/daily",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_daily_analytics(
    request: Any,
    days: int = Query(30, ge=1, le=90, description="Период в днях"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить дневную динамику платежей.

    Возвращает статистику по дням:
    - Количество транзакций
    - Сумма
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = repository.get_analytics(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
    )

    # Преобразуем daily_stats в список для удобства
    daily_list = [
        {
            "date": date,
            "count": stats["count"],
            "amount": stats["amount"],
        }
        for date, stats in sorted(analytics.get("daily_stats", {}).items())
    ]

    return {
        "period": analytics["period"],
        "summary": analytics["summary"],
        "daily": daily_list,
    }


@router.get(
    "/analytics/status",
    tags=["Payment Analytics"],
)
@limiter.limit("30/minute")
async def get_status_analytics(
    request: Any,
    days: int = Query(30, ge=1, le=365, description="Период в днях"),
    tenant_id: Optional[int] = Query(None, description="Фильтр по tenant"),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить аналитику по статусам платежей.

    Возвращает распределение транзакций по статусам.
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = repository.get_analytics(
        start_date=start_date,
        end_date=end_date,
        tenant_id=tenant_id,
    )

    total = analytics["summary"]["total_transactions"]
    by_status = analytics.get("by_status", {})

    # Добавляем проценты
    status_with_percentage = {}
    for s, count in by_status.items():
        status_with_percentage[s] = {
            "count": count,
            "percentage": round(count / max(total, 1) * 100, 2),
        }

    return {
        "period": analytics["period"],
        "total_transactions": total,
        "by_status": status_with_percentage,
    }
