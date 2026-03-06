"""Тесты идемпотентности webhook'ов."""

import pytest
from sqlalchemy.orm import Session
from app.models.payment import Payment, PaymentStatus
from app.services.payment_service import (
    create_payment_record,
    update_payment_status,
    check_webhook_idempotency,
    mark_webhook_processed,
)


class TestWebhookIdempotency:
    """Тесты идемпотентности webhook'ов."""

    @pytest.fixture
    def payment(self, db_session: Session) -> Payment:
        """Создание тестового платежа."""
        return create_payment_record(
            db=db_session,
            order_id="test_order_123",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test payment",
        )

    def test_initial_webhook_processed_empty(self, payment: Payment):
        """Проверка, что изначально webhook_processed пуст."""
        assert payment.webhook_processed == ""
        assert payment.is_webhook_processed("event_123") is False

    def test_mark_webhook_processed(self, payment: Payment):
        """Проверка отметки webhook как обработанного."""
        payment.mark_webhook_processed("event_123")
        assert payment.is_webhook_processed("event_123") is True

    def test_mark_multiple_webhooks(self, payment: Payment):
        """Проверка отметки нескольких webhook'ов."""
        payment.mark_webhook_processed("event_123")
        payment.mark_webhook_processed("event_456")
        payment.mark_webhook_processed("event_789")

        assert payment.is_webhook_processed("event_123") is True
        assert payment.is_webhook_processed("event_456") is True
        assert payment.is_webhook_processed("event_789") is True
        assert payment.is_webhook_processed("event_999") is False

    def test_mark_same_webhook_twice(self, payment: Payment):
        """Проверка, что повторная отметка не создаёт дубликат."""
        payment.mark_webhook_processed("event_123")
        payment.mark_webhook_processed("event_123")

        processed = payment.webhook_processed.split(",")
        assert processed.count("event_123") == 1

    def test_check_webhook_idempotency_function(
        self, db_session: Session, payment: Payment
    ):
        """Проверка функции check_webhook_idempotency."""
        order_id = "test_order_123"
        event_id = "event_123"

        # Initially not processed
        assert check_webhook_idempotency(db_session, order_id, event_id) is False

        # Mark as processed
        mark_webhook_processed(db_session, order_id, event_id)

        # Now should be processed
        assert check_webhook_idempotency(db_session, order_id, event_id) is True

    def test_update_payment_status_with_webhook_event_id(
        self, db_session: Session, payment: Payment
    ):
        """Проверка update_payment_status с webhook_event_id."""
        order_id = "test_order_123"
        event_id = "event_123"

        # First update should succeed
        result = update_payment_status(
            db=db_session,
            order_id=order_id,
            status="completed",
            webhook_event_id=event_id,
        )
        assert result is not None
        assert result.status == "completed"
        assert result.is_webhook_processed(event_id) is True

        # Second update with same event_id should return same payment without changes
        result2 = update_payment_status(
            db=db_session,
            order_id=order_id,
            status="failed",  # Different status
            webhook_event_id=event_id,  # Same event_id
        )
        assert result2 is not None
        assert result2.status == "completed"  # Status unchanged
        assert result2.is_webhook_processed(event_id) is True

    def test_update_payment_status_different_events(
        self, db_session: Session, payment: Payment
    ):
        """Проверка update_payment_status с разными event_id."""
        order_id = "test_order_123"

        # First event
        result1 = update_payment_status(
            db=db_session,
            order_id=order_id,
            status="completed",
            webhook_event_id="event_123",
        )
        assert result1.status == "completed"

        # Second event should update status
        result2 = update_payment_status(
            db=db_session,
            order_id=order_id,
            status="refunded",
            webhook_event_id="event_456",
        )
        assert result2.status == "refunded"

    def test_webhook_processed_format(self, payment: Payment):
        """Проверка формата хранения webhook_processed."""
        payment.mark_webhook_processed("event_1")
        payment.mark_webhook_processed("event_2")
        payment.mark_webhook_processed("event_3")

        assert payment.webhook_processed == "event_1,event_2,event_3"

    def test_to_dict_includes_webhook_processed(self, payment: Payment):
        """Проверка, что to_dict включает webhook_processed."""
        payment.mark_webhook_processed("event_123")
        payment_dict = payment.to_dict()

        assert "webhook_processed" in payment_dict
        assert "event_123" in payment_dict["webhook_processed"]
