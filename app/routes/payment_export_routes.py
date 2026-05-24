"""
Payment export routes.

Endpoints для экспорта данных о платежах:
- CSV export
- JSON export (будущее расширение)
"""

import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.payment import Payment, PaymentStatus
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
            detail="Admin role required to export payment data",
        )
    return current_user


@router.get(
    "/export/csv",
    response_class=StreamingResponse,
    tags=["Payment Export"],
)
@limiter.limit("10/minute")
async def export_payments_csv(
    request: Any,
    start_date: Optional[str] = Query(
        None,
        description="Начальная дата (ISO 8601, e.g., 2024-01-01)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Конечная дата (ISO 8601, e.g., 2024-12-31)",
    ),
    gateway: Optional[str] = Query(
        None,
        description="Фильтр по платёжной системе",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Фильтр по статусу",
    ),
    tenant_id: Optional[int] = Query(
        None,
        description="Фильтр по tenant ID",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Период в днях (если не указаны start_date/end_date)",
    ),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> StreamingResponse:
    """
    Экспорт платежей в CSV формате.
    
    - **start_date**: Начальная дата (ISO 8601)
    - **end_date**: Конечная дата (ISO 8601)
    - **gateway**: Фильтр по платёжной системе (yookassa, tinkoff, etc.)
    - **status**: Фильтр по статусу платежа
    - **tenant_id**: Фильтр по tenant ID
    - **days**: Период в днях (если не указаны даты)
    
    Возвращает CSV файл с полями:
    id, order_id, transaction_id, gateway, amount, currency, status, 
    description, created_at, updated_at, tenant_id
    """
    # Определяем период
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}. Use ISO 8601 (e.g., 2024-01-01)",
            )
    else:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
    
    payments = repository.get_payments_by_period(
        start_date=start_dt,
        end_date=end_dt,
        gateway=gateway,
        status=status_filter,
        tenant_id=tenant_id,
    )
    # Enforce maximum record limit to prevent DoS / OOM
    MAX_EXPORT_RECORDS = 100_000
    payments_list = list(payments)
    if len(payments_list) > MAX_EXPORT_RECORDS:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Export exceeds maximum record limit of {MAX_EXPORT_RECORDS}. "
                   f"Please narrow your date range or filters.",
        )
    
    # Создаём CSV в памяти
    output = io.StringIO()
    fieldnames = [
        'id',
        'order_id',
        'transaction_id',
        'payment_gateway',
        'amount',
        'currency',
        'status',
        'description',
        'created_at',
        'updated_at',
        'tenant_id',
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
    writer.writeheader()
    
    for payment in payments:
        writer.writerow({
            'id': payment.id,
            'order_id': payment.order_id,
            'transaction_id': payment.transaction_id or '',
            'payment_gateway': payment.payment_gateway,
            'amount': f"{payment.amount:.2f}",
            'currency': payment.currency or 'RUB',
            'status': payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
            'description': (payment.description or '').replace('\n', ' '),
            'created_at': payment.created_at.isoformat() if payment.created_at else '',
            'updated_at': payment.updated_at.isoformat() if payment.updated_at else '',
            'tenant_id': payment.tenant_id or '',
        })
    
    # Формируем имя файла
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"payments_export_{timestamp}.csv"
    
    # Создаём StreamingResponse
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Total-Records": str(len(payments)),
            "X-Export-Date": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get(
    "/export/json",
    tags=["Payment Export"],
)
@limiter.limit("10/minute")
async def export_payments_json(
    request: Any,
    start_date: Optional[str] = Query(
        None,
        description="Начальная дата (ISO 8601)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="Конечная дата (ISO 8601)",
    ),
    gateway: Optional[str] = Query(
        None,
        description="Фильтр по платёжной системе",
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Фильтр по статусу",
    ),
    tenant_id: Optional[int] = Query(
        None,
        description="Фильтр по tenant ID",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Период в днях",
    ),
    repository: PaymentRepository = Depends(get_repository),
    current_user: User = Depends(get_current_admin_user),
) -> dict:
    """
    Экспорт платежей в JSON формате.
    
    Возвращает JSON объект со списком платежей и метаданными.
    """
    # Определяем период
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format: {str(e)}. Use ISO 8601",
            )
    else:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
    
    payments = repository.get_payments_by_period(
        start_date=start_dt,
        end_date=end_dt,
        gateway=gateway,
        status=status_filter,
        tenant_id=tenant_id,
    )
    
    # Считаем статистику
    total_amount = sum(p.amount for p in payments)
    by_status = {}
    by_gateway = {}
    
    for payment in payments:
        status_val = payment.status.value if hasattr(payment.status, 'value') else str(payment.status)
        gateway_val = payment.payment_gateway
        
        by_status[status_val] = by_status.get(status_val, 0) + 1
        by_gateway[gateway_val] = by_gateway.get(gateway_val, 0) + 1
    
    return {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
        },
        "filters": {
            "gateway": gateway,
            "status": status_filter,
            "tenant_id": tenant_id,
        },
        "summary": {
            "total_records": len(payments),
            "total_amount": round(total_amount, 2),
            "by_status": by_status,
            "by_gateway": by_gateway,
        },
        "payments": [
            {
                "id": p.id,
                "order_id": p.order_id,
                "transaction_id": p.transaction_id,
                "payment_gateway": p.payment_gateway,
                "amount": p.amount,
                "currency": p.currency or "RUB",
                "status": p.status.value if hasattr(p.status, 'value') else str(p.status),
                "description": p.description,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "tenant_id": p.tenant_id,
            }
            for p in payments
        ],
    }
