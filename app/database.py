from typing import Generator
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from app.settings import settings
import logging

logger = logging.getLogger(__name__)

# Для SQLite используем обычный драйвер
database_url = settings.database_url
if database_url.startswith("sqlite+aiosqlite"):
    database_url = database_url.replace("sqlite+aiosqlite", "sqlite")

# Конфигурация pool для SQLite
connect_args = {"check_same_thread": False}
if "sqlite" in database_url:
    poolclass = StaticPool
else:
    poolclass = None
    connect_args = {}

engine = create_engine(
    database_url,
    connect_args=connect_args,
    poolclass=poolclass,
    pool_pre_ping=True,
    pool_recycle=3600,
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
