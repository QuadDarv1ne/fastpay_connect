"""Зависимости для внедрения."""

import asyncio
from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import check_db_connection, get_db
from app.repositories.payment_repository import PaymentRepository

__all__ = ["get_db", "get_payment_repository", "verify_db_connection"]


def get_payment_repository(db: Session = Depends(get_db)) -> PaymentRepository:
    """Получить репозиторий платежей."""
    return PaymentRepository(db)


async def verify_db_connection() -> bool:
    """Проверить подключение к БД."""
    ok = await asyncio.to_thread(check_db_connection)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    return True
