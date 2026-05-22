"""Асинхронная поддержка базы данных.

Модуль предоставляет асинхронные утилиты для работы с SQLAlchemy
в асинхронном FastAPI приложении.
"""

from typing import AsyncGenerator, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    async_scoped_session,
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from app.settings import settings
import logging

logger = logging.getLogger(__name__)

# ==================== Sync Engine (для обратной совместимости) ====================
sync_database_url = settings.database_url
if sync_database_url.startswith("sqlite+aiosqlite"):
    sync_database_url = sync_database_url.replace("sqlite+aiosqlite", "sqlite")

sync_connect_args = {"check_same_thread": False} if "sqlite" in sync_database_url else {}
sync_poolclass = StaticPool if "sqlite" in sync_database_url else None

sync_engine = create_engine(
    sync_database_url,
    connect_args=sync_connect_args,
    poolclass=sync_poolclass,
    pool_pre_ping=True,
    pool_recycle=3600,
)

SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
Base = declarative_base()


def get_sync_db() -> Generator:
    """Получение синхронной сессии БД (для обратной совместимости)."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Async Engine ====================
async_database_url = settings.database_url

# Преобразуем URL для async драйверов
if async_database_url.startswith("sqlite:///"):
    async_database_url = async_database_url.replace("sqlite:///", "sqlite+aiosqlite://")
elif async_database_url.startswith("postgresql://"):
    async_database_url = async_database_url.replace("postgresql://", "postgresql+asyncpg://")
elif async_database_url.startswith("mysql://"):
    async_database_url = async_database_url.replace("mysql://", "mysql+aiomysql://")

async_connect_args = {"check_same_thread": False} if "sqlite" in async_database_url else {}

async_engine: AsyncEngine = create_async_engine(
    async_database_url,
    connect_args=async_connect_args,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Получение асинхронной сессии БД.

    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_async_db():
    """Асинхронная инициализация БД."""
    from app.models.payment import Payment
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.webhook_event import WebhookEvent

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Async database tables created successfully")


async def check_async_db_connection() -> bool:
    """Проверка асинхронного подключения к БД."""
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Async database connection check failed: {e}")
        return False


async def dispose_async_engine():
    """Закрытие асинхронного движка."""
    await async_engine.dispose()


# ==================== Helper Functions ====================
def get_engine_url() -> str:
    """URL для alembic."""
    return settings.database_url


def get_async_engine_url() -> str:
    """Асинхронный URL для alembic."""
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite://")
    elif url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    return url
