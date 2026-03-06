"""Зависимости для внедрения."""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.repositories.payment_repository import PaymentRepository


def get_db() -> Generator[Session, None, None]:
    """Получить сессию БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_payment_repository(db: Session = Depends(get_db)) -> PaymentRepository:
    """Получить репозиторий платежей."""
    return PaymentRepository(db)
