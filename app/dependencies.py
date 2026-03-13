"""Зависимости для внедрения."""

from typing import Generator

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, check_db_connection
from app.repositories.payment_repository import PaymentRepository


def get_db() -> Generator[Session, None, None]:
    """Получить сессию БД."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable"
        ) from e
    finally:
        db.close()


def get_payment_repository(db: Session = Depends(get_db)) -> PaymentRepository:
    """Получить репозиторий платежей."""
    return PaymentRepository(db)


async def verify_db_connection() -> bool:
    """Проверить подключение к БД."""
    if not check_db_connection():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )
    return True
