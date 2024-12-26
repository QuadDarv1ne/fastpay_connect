from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Создаем движок для подключения к базе данных
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # Для SQLite

# Базовый класс для всех моделей
Base = declarative_base()

# Сессия для работы с базой данных
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    Функция для получения сессии с базой данных.
    
    :return: Объект сессии базы данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
