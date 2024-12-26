from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import DATABASE_URL

# Создаем движок для подключения к базе данных в зависимости от СУБД
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})  # Для SQLite

'''
Для PostgreSQL, MySQL, SQL Server и других СУБД:
- PostgreSQL:
  engine = create_engine("postgresql://username:password@localhost/dbname")
- MySQL:
  engine = create_engine("mysql+pymysql://username:password@localhost/dbname")
- SQL Server:
  engine = create_engine("mssql+pyodbc://username:password@localhost/dbname?driver=ODBC+Driver+17+for+SQL+Server")
- MongoDB:
  Для MongoDB используйте PyMongo, так как это не реляционная база данных.
'''

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
