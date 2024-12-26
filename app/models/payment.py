from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Payment(Base):
    """
    Модель для хранения информации о платежах.

    Атрибуты:
        id (int): Уникальный идентификатор платежа.
        order_id (str): Уникальный идентификатор заказа, связанный с платежом.
        amount (float): Сумма платежа.
        currency (str): Валюта платежа, по умолчанию "RUB".
        status (str): Статус платежа (например, "pending", "completed").
        description (str): Описание платежа.
        created_at (datetime): Время создания записи.
        updated_at (datetime): Время последнего обновления записи.

    Методы:
        __repr__ (str): Строковое представление объекта модели.
    """
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True)
    amount = Column(Float)
    currency = Column(String, default="RUB")
    status = Column(String, default="pending")
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        """
        Возвращает строковое представление объекта модели Payment.
        
        Возвращает:
            str: Строковое представление объекта с информацией о заказе, сумме и статусе.
        """
        return f"<Payment(order_id={self.order_id}, amount={self.amount}, status={self.status})>"
