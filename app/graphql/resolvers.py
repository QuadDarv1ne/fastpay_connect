"""
GraphQL resolvers для FastPay Connect.
"""

import strawberry
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func
from enum import Enum

from app.models.payment import Payment as PaymentModel, PaymentStatus
from app.database import SessionLocal


# Определяем типы GraphQL локально для избежания циклических импортов
@strawberry.enum
class PaymentStatusEnum(Enum):
    """Статусы платежа."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@strawberry.type
class Payment:
    """Тип платежа GraphQL."""
    id: int
    order_id: str
    payment_id: Optional[str]
    transaction_id: Optional[str]
    payment_gateway: str
    amount: float
    currency: str
    status: PaymentStatusEnum
    description: Optional[str]
    payment_url: Optional[str]
    created_at: str
    updated_at: str


@strawberry.type
class PaymentConnection:
    """Пагинированный список платежей."""
    items: List[Payment]
    total: int
    page: int
    page_size: int
    pages: int


@strawberry.type
class PaymentStatistics:
    """Статистика по платежам."""
    total_payments: int
    total_amount: float
    by_status: strawberry.scalars.JSON
    by_gateway: strawberry.scalars.JSON


def get_db() -> Session:
    """Получить сессию БД."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def payment_model_to_graphql(payment: PaymentModel) -> Payment:
    """Конвертация модели Payment в GraphQL тип."""
    return Payment(
        id=payment.id,
        order_id=payment.order_id,
        payment_id=payment.payment_id,
        transaction_id=payment.transaction_id,
        payment_gateway=payment.payment_gateway,
        amount=payment.amount,
        currency=payment.currency,
        status=PaymentStatusEnum(payment.status),
        description=payment.description,
        payment_url=payment.payment_url,
        created_at=payment.created_at.isoformat() if payment.created_at else None,
        updated_at=payment.updated_at.isoformat() if payment.updated_at else None,
    )


@strawberry.type
class PaymentQuery:
    """Query resolver для платежей."""
    
    @strawberry.field
    def payment(self, order_id: str) -> Optional[Payment]:
        """Получить платёж по order_id."""
        db = get_db()
        payment = db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()
        db.close()
        
        if not payment:
            return None
        
        return payment_model_to_graphql(payment)
    
    @strawberry.field
    def payments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[PaymentStatusEnum] = None,
        gateway: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaymentConnection:
        """Получить список платежей с пагинацией и фильтрами."""
        db = get_db()
        
        query = db.query(PaymentModel)
        
        # Фильтры
        if status:
            query = query.filter(PaymentModel.status == status.value)
        
        if gateway:
            query = query.filter(PaymentModel.payment_gateway == gateway)
        
        if search:
            query = query.filter(
                (PaymentModel.order_id.ilike(f"%{search}%")) |
                (PaymentModel.payment_id.ilike(f"%{search}%"))
            )
        
        # Общее количество
        total = query.count()
        
        # Сортировка
        sort_column = getattr(PaymentModel, sort_by, PaymentModel.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Пагинация
        offset = (page - 1) * page_size
        payments = query.offset(offset).limit(page_size).all()
        db.close()
        
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        return PaymentConnection(
            items=[payment_model_to_graphql(p) for p in payments],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
    
    @strawberry.field
    def statistics(self) -> PaymentStatistics:
        """Получить статистику по платежам."""
        db = get_db()
        
        total = db.query(PaymentModel).count()
        
        by_status_query = db.query(
            PaymentModel.status, func.count(PaymentModel.id)
        ).group_by(PaymentModel.status).all()
        
        by_gateway_query = db.query(
            PaymentModel.payment_gateway, func.count(PaymentModel.id)
        ).group_by(PaymentModel.payment_gateway).all()
        
        total_amount_result = db.query(func.sum(PaymentModel.amount)).filter(
            PaymentModel.status == PaymentStatus.COMPLETED.value
        ).scalar() or 0.0
        
        db.close()
        
        return PaymentStatistics(
            total_payments=total,
            total_amount=float(total_amount_result),
            by_status={status: count for status, count in by_status_query},
            by_gateway={gateway: count for gateway, count in by_gateway_query},
        )


@strawberry.type
class PaymentMutation:
    """Mutation resolver для платежей."""
    
    @strawberry.field
    def ping(self) -> str:
        """Test mutation."""
        return "pong"


# Объединяем query и mutation
@strawberry.type
class GraphQLQuery(PaymentQuery):
    """Объединённый Query."""
    pass


@strawberry.type
class GraphQLMutation(PaymentMutation):
    """Объединённый Mutation."""
    pass


schema = strawberry.Schema(query=GraphQLQuery, mutation=GraphQLMutation)
