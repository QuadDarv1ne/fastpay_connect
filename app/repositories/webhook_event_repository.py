"""
Repository для работы с WebhookEvent.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import logging
import json

from app.models.webhook_event import WebhookEvent, WebhookEventStatus
from app.models.payment import Payment

logger = logging.getLogger(__name__)


class WebhookEventRepository:
    """Репозиторий для работы с webhook событиями."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        event_id: str,
        order_id: str,
        gateway: str,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 5,
    ) -> Optional[WebhookEvent]:
        """Создать новое webhook событие."""
        try:
            # Проверка на дубликат
            existing = self.get_by_event_id(event_id)
            if existing:
                logger.warning(f"Webhook event {event_id} already exists")
                return existing

            event = WebhookEvent(
                event_id=event_id,
                order_id=order_id,
                gateway=gateway,
                status=WebhookEventStatus.PENDING,
                retry_count=0,
                max_retries=max_retries,
                payload=payload,
            )

            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)

            logger.info(f"Webhook event {event_id} created for order {order_id}")
            return event

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating webhook event: {e}")
            return None

    def get_by_event_id(self, event_id: str) -> Optional[WebhookEvent]:
        """Получить событие по event_id."""
        return self.db.query(WebhookEvent).filter(
            WebhookEvent.event_id == event_id
        ).first()

    def get_by_order_id(self, order_id: str) -> List[WebhookEvent]:
        """Получить все события для заказа."""
        return self.db.query(WebhookEvent).filter(
            WebhookEvent.order_id == order_id
        ).order_by(WebhookEvent.created_at.desc()).all()

    def update_status(
        self,
        event: WebhookEvent,
        status: WebhookEventStatus,
        error: Optional[str] = None,
    ) -> Optional[WebhookEvent]:
        """Обновить статус события."""
        try:
            event.status = status
            event.updated_at = datetime.now(timezone.utc)

            if error:
                event.last_error = error

            if status == WebhookEventStatus.SUCCESS:
                event.processed_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(event)
            return event

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating webhook event: {e}")
            return None

    def increment_retry(
        self,
        event: WebhookEvent,
        error: str,
        next_retry_at: Optional[datetime] = None,
    ) -> Optional[WebhookEvent]:
        """Увеличить счётчик попыток."""
        try:
            event.retry_count += 1
            event.last_error = error
            event.next_retry_at = next_retry_at
            event.status = WebhookEventStatus.RETRY
            event.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(event)
            return event

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error incrementing retry: {e}")
            return None

    def mark_failed(self, event: WebhookEvent, error: str) -> Optional[WebhookEvent]:
        """Отметить событие как неудачное."""
        try:
            event.status = WebhookEventStatus.FAILED
            event.last_error = error
            event.updated_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(event)
            return event

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error marking failed: {e}")
            return None

    def get_events_for_retry(self, limit: int = 100) -> List[WebhookEvent]:
        """Получить события, требующие повторной обработки."""
        now = datetime.now(timezone.utc)
        return self.db.query(WebhookEvent).filter(
            and_(
                WebhookEvent.status == WebhookEventStatus.RETRY,
                or_(
                    WebhookEvent.next_retry_at.is_(None),
                    WebhookEvent.next_retry_at <= now,
                ),
                WebhookEvent.retry_count < WebhookEvent.max_retries,
            )
        ).limit(limit).all()

    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Получить общую статистику."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        # Общая статистика
        total = self.db.query(WebhookEvent).filter(
            WebhookEvent.created_at >= since
        ).count()

        by_status = self.db.query(
            WebhookEvent.status, func.count(WebhookEvent.id)
        ).filter(
            WebhookEvent.created_at >= since
        ).group_by(WebhookEvent.status).all()

        by_gateway = self.db.query(
            WebhookEvent.gateway, func.count(WebhookEvent.id)
        ).filter(
            WebhookEvent.created_at >= since
        ).group_by(WebhookEvent.gateway).all()

        # Статистика по retry
        retrying = self.db.query(WebhookEvent).filter(
            WebhookEvent.status == WebhookEventStatus.RETRY
        ).count()

        failed = self.db.query(WebhookEvent).filter(
            WebhookEvent.status == WebhookEventStatus.FAILED
        ).count()

        return {
            "total": total,
            "by_status": {status.value: count for status, count in by_status},
            "by_gateway": {gateway: count for gateway, count in by_gateway},
            "retrying": retrying,
            "failed": failed,
            "period_days": days,
        }

    def get_dashboard_stats(self, limit: int = 10) -> Dict[str, Any]:
        """Получить расширенную статистику для дашборда."""
        # Последние события
        recent_events = self.db.query(WebhookEvent).order_by(
            WebhookEvent.created_at.desc()
        ).limit(limit).all()

        # Статистика по статусам
        stats = self.get_statistics()

        # Топ gateways по ошибкам
        error_stats = self.db.query(
            WebhookEvent.gateway, func.count(WebhookEvent.id)
        ).filter(
            WebhookEvent.status == WebhookEventStatus.FAILED
        ).group_by(WebhookEvent.gateway).all()

        # Средняя обработка по времени
        avg_processing_time = None  # Можно добавить вычисление

        return {
            "total_events": stats["total"],
            "by_status": stats["by_status"],
            "by_gateway": stats["by_gateway"],
            "recent_events": [event.to_dict() for event in recent_events],
            "retrying_count": stats["retrying"],
            "failed_count": stats["failed"],
            "error_by_gateway": {gw: cnt for gw, cnt in error_stats},
            "avg_processing_time": avg_processing_time,
        }

    def get_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        gateway: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[WebhookEvent], int]:
        """Получить события с пагинацией."""
        query = self.db.query(WebhookEvent)

        if gateway:
            query = query.filter(WebhookEvent.gateway == gateway)

        if status:
            query = query.filter(WebhookEvent.status == WebhookEventStatus(status))

        total = query.count()
        events = query.order_by(
            WebhookEvent.created_at.desc()
        ).offset((page - 1) * page_size).limit(page_size).all()

        return events, total

    def cleanup_old_events(self, days: int = 30) -> int:
        """Удалить старые события."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            deleted = self.db.query(WebhookEvent).filter(
                WebhookEvent.created_at < cutoff,
                WebhookEvent.status.in_([WebhookEventStatus.SUCCESS, WebhookEventStatus.FAILED]),
            ).delete(synchronize_session=False)

            self.db.commit()
            logger.info(f"Cleaned up {deleted} old webhook events")
            return deleted

        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error cleaning up events: {e}")
            return 0
