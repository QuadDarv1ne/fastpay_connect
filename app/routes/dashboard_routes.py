"""
Routes для Payment Statistics Dashboard.
"""

from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.dependencies import get_payment_repository
from app.utils.security import get_current_user
from app.models.user import User
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

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


@router.get("/ui", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def payment_dashboard_ui(
    request: Request,
    current_user: User = Depends(get_current_admin_user),
) -> HTMLResponse:
    """
    UI Dashboard для статистики платежей.
    """
    from pathlib import Path
    from fastapi.templating import Jinja2Templates
    
    templates_dir = Path(__file__).parent.parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    
    return templates.TemplateResponse(
        "payment_dashboard.html",
        {"request": request}
    )


@router.get("/summary")
@limiter.limit("30/minute")
async def get_dashboard_summary(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Period in days"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить сводную статистику для дашборда.
    """
    from app.repositories.payment_repository import PaymentRepository
    
    stats = repository.get_statistics()
    
    # Дополнительная статистика
    db = repository._db
    from app.models.payment import Payment, PaymentStatus
    
    now = datetime.now()
    date_from = now - timedelta(days=days)
    
    # Платежи за период
    period_payments = db.query(Payment).filter(
        Payment.created_at >= date_from
    ).all()
    
    # Новые платежи за период
    new_payments = len([p for p in period_payments if p.created_at >= date_from])
    
    # Конверсия (completed / total)
    completed = len([p for p in period_payments if p.status == PaymentStatus.COMPLETED.value])
    conversion_rate = (completed / len(period_payments) * 100) if period_payments else 0
    
    # Средний чек
    avg_check = sum(p.amount for p in period_payments if p.status == PaymentStatus.COMPLETED.value)
    avg_check = avg_check / completed if completed > 0 else 0
    
    # Топ gateway по сумме
    gateway_amounts = {}
    for p in period_payments:
        if p.status == PaymentStatus.COMPLETED.value:
            gateway_amounts[p.payment_gateway] = gateway_amounts.get(p.payment_gateway, 0) + p.amount
    
    top_gateway = max(gateway_amounts.items(), key=lambda x: x[1]) if gateway_amounts else (None, 0)
    
    return {
        "status": "success",
        "data": {
            "total_payments": stats["total_payments"],
            "total_amount": stats["total_completed_amount"],
            "by_status": stats["by_status"],
            "by_gateway": stats["by_gateway"],
            "period_days": days,
            "new_payments": new_payments,
            "conversion_rate": round(conversion_rate, 2),
            "average_check": round(avg_check, 2),
            "top_gateway": {
                "name": top_gateway[0],
                "amount": round(top_gateway[1], 2)
            } if top_gateway[0] else None,
        }
    }


@router.get("/daily-stats")
@limiter.limit("30/minute")
async def get_daily_statistics(
    request: Request,
    days: int = Query(default=30, ge=1, le=90, description="Number of days"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить ежедневную статистику.
    """
    from sqlalchemy import func
    from app.models.payment import Payment, PaymentStatus
    from datetime import date
    
    db = repository._db
    date_from = datetime.now() - timedelta(days=days)
    
    # Группировка по дням
    daily_stats = db.query(
        func.date(Payment.created_at).label('date'),
        func.count(Payment.id).label('total'),
        func.sum(Payment.amount).label('amount'),
    ).filter(
        Payment.created_at >= date_from
    ).group_by(
        func.date(Payment.created_at)
    ).order_by(
        func.date(Payment.created_at)
    ).all()
    
    # Статусы по дням
    daily_status_stats = db.query(
        func.date(Payment.created_at).label('date'),
        Payment.status,
        func.count(Payment.id).label('count'),
    ).filter(
        Payment.created_at >= date_from
    ).group_by(
        func.date(Payment.created_at),
        Payment.status
    ).all()
    
    # Формируем ответ
    result = []
    for stat in daily_stats:
        day_data = {
            "date": str(stat.date),
            "total_payments": stat.total,
            "total_amount": float(stat.amount) if stat.amount else 0,
            "by_status": {}
        }
        
        for status_stat in daily_status_stats:
            if status_stat.date == stat.date:
                day_data["by_status"][status_stat.status] = status_stat.count
        
        result.append(day_data)
    
    return {
        "status": "success",
        "data": result
    }


@router.get("/gateway-stats")
@limiter.limit("30/minute")
async def get_gateway_statistics(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить статистику по платёжным системам.
    """
    from sqlalchemy import func
    from app.models.payment import Payment, PaymentStatus
    
    db = repository._db
    date_from = datetime.now() - timedelta(days=days)
    
    # Общая статистика по gateway
    gateway_stats = db.query(
        Payment.payment_gateway,
        func.count(Payment.id).label('total'),
        func.sum(Payment.amount).label('amount'),
    ).filter(
        Payment.created_at >= date_from
    ).group_by(
        Payment.payment_gateway
    ).all()
    
    # Статусы по gateway
    gateway_status_stats = db.query(
        Payment.payment_gateway,
        Payment.status,
        func.count(Payment.id).label('count'),
    ).filter(
        Payment.created_at >= date_from
    ).group_by(
        Payment.payment_gateway,
        Payment.status
    ).all()
    
    # Формируем ответ
    result = []
    for stat in gateway_stats:
        gateway_data = {
            "gateway": stat.payment_gateway,
            "total_payments": stat.total,
            "total_amount": float(stat.amount) if stat.amount else 0,
            "by_status": {}
        }
        
        for status_stat in gateway_status_stats:
            if status_stat.payment_gateway == stat.payment_gateway:
                gateway_data["by_status"][status_stat.status] = status_stat.count
        
        # Success rate
        success = gateway_data["by_status"].get(PaymentStatus.COMPLETED.value, 0)
        gateway_data["success_rate"] = round(success / stat.total * 100, 2) if stat.total > 0 else 0
        
        result.append(gateway_data)
    
    # Сортируем по amount
    result.sort(key=lambda x: x["total_amount"], reverse=True)
    
    return {
        "status": "success",
        "data": result
    }


@router.get("/status-distribution")
@limiter.limit("30/minute")
async def get_status_distribution(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Number of days"),
    repository: PaymentRepository = Depends(get_payment_repository),
    current_user: User = Depends(get_current_admin_user),
) -> Dict[str, Any]:
    """
    Получить распределение по статусам.
    """
    from sqlalchemy import func
    from app.models.payment import Payment
    
    db = repository._db
    date_from = datetime.now() - timedelta(days=days)
    
    status_stats = db.query(
        Payment.status,
        func.count(Payment.id).label('count'),
        func.sum(Payment.amount).label('amount'),
    ).filter(
        Payment.created_at >= date_from
    ).group_by(
        Payment.status
    ).all()
    
    total = sum(stat.count for stat in status_stats)
    
    result = []
    for stat in status_stats:
        result.append({
            "status": stat.status,
            "count": stat.count,
            "percentage": round(stat.count / total * 100, 2) if total > 0 else 0,
            "amount": float(stat.amount) if stat.amount else 0,
        })
    
    # Сортируем по count
    result.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "status": "success",
        "data": result
    }
