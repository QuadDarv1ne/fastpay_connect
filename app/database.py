from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.settings import settings

# Синхронный движок для SQLAlchemy
engine = create_engine(
    settings.database_url, 
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

Base = declarative_base()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator:
    """Получение сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация БД."""
    from app.models.payment import Payment
    Base.metadata.create_all(bind=engine)


def get_engine_url():
    """URL для alembic."""
    return settings.database_url
