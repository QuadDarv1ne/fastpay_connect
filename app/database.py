from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from app.settings import settings
import logging

logger = logging.getLogger(__name__)

# Для SQLite используем обычный драйвер
database_url = settings.database_url
if database_url.startswith("sqlite+aiosqlite"):
    database_url = database_url.replace("sqlite+aiosqlite", "sqlite")

# Конфигурация pool для SQLite
# QueuePool вместо StaticPool — StaticPool использует одно соединение на все
# потоки, что вызывает race conditions и data corruption в production
if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}
    pool_kwargs: dict = {
        "poolclass": QueuePool,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
    }
else:
    connect_args = {}
    pool_kwargs = {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    pool_recycle=3600,
    **pool_kwargs,
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
    from app.models.user import User
    from app.models.tenant import Tenant
    from app.models.webhook_event import WebhookEvent
    from app.models.audit_log import AuditLog
    from app.models.subscription import Subscription
    from app.models.split_payment import SplitPayment
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def check_db_connection() -> bool:
    """Проверка подключения к БД."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_engine_url() -> str:
    """URL для alembic."""
    return settings.database_url


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Настройка SQLite pragma для целостности данных."""
    if "sqlite" in database_url:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
