from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Создаем движок для подключения к базе данных
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Базовый класс для всех моделей
Base = declarative_base()

# Сессия для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Функция для получения сессии с базой данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Инициализация базы данных (создание таблиц)."""
    from app.models.payment import Payment
    Base.metadata.create_all(bind=engine)


def get_engine_url():
    """Возвращает URL для alembic."""
    return DATABASE_URL
