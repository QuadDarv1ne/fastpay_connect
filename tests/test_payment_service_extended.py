import pytest
from datetime import datetime, timezone, timedelta
from app.services.payment_service import (
    create_payment_record,
    update_payment_status,
    get_payment_by_order_id,
    get_payment_by_id,
    get_payments_by_status,
    get_payments_by_gateway,
    get_payments_by_date_range,
    refund_payment,
    cancel_payment,
    get_payment_statistics,
)
from app.models.payment import PaymentStatus


class TestPaymentService:
    def test_get_payments_by_status(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_status_1",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test 1",
        )
        create_payment_record(
            db=db_session,
            order_id="order_status_2",
            payment_gateway="yookassa",
            amount=2000.0,
            description="Test 2",
        )

        payments = get_payments_by_status(db_session, PaymentStatus.PENDING.value)
        assert len(payments) >= 2

    def test_get_payments_by_gateway(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_gateway_1",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )
        create_payment_record(
            db=db_session,
            order_id="order_gateway_2",
            payment_gateway="tinkoff",
            amount=2000.0,
            description="Test",
        )

        yookassa_payments = get_payments_by_gateway(db_session, "yookassa")
        tinkoff_payments = get_payments_by_gateway(db_session, "tinkoff")

        assert len(yookassa_payments) >= 1
        assert len(tinkoff_payments) >= 1

    def test_refund_payment(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_refund",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test refund",
        )

        refunded = refund_payment(
            db_session, order_id="order_refund", reason="Customer request"
        )

        assert refunded is not None
        assert refunded.status == PaymentStatus.REFUNDED.value

    def test_refund_already_refunded(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_refund_2",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )
        refund_payment(db_session, order_id="order_refund_2")

        result = refund_payment(db_session, order_id="order_refund_2")
        assert result is not None
        assert result.status == PaymentStatus.REFUNDED.value

    def test_refund_not_found(self, db_session):
        result = refund_payment(db_session, order_id="nonexistent")
        assert result is None

    def test_cancel_payment(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_cancel",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test cancel",
        )

        cancelled = cancel_payment(
            db_session, order_id="order_cancel", reason="Customer request"
        )

        assert cancelled is not None
        assert cancelled.status == PaymentStatus.CANCELLED.value

    def test_cancel_completed_payment(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_cancel_2",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )
        update_payment_status(
            db_session, order_id="order_cancel_2", status=PaymentStatus.COMPLETED.value
        )

        result = cancel_payment(db_session, order_id="order_cancel_2")
        assert result is not None
        assert result.status == PaymentStatus.COMPLETED.value

    def test_cancel_not_found(self, db_session):
        result = cancel_payment(db_session, order_id="nonexistent")
        assert result is None

    def test_get_payment_statistics(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_stats_1",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test 1",
        )
        create_payment_record(
            db=db_session,
            order_id="order_stats_2",
            payment_gateway="tinkoff",
            amount=2000.0,
            description="Test 2",
        )

        stats = get_payment_statistics(db_session)

        assert "total_payments" in stats
        assert "by_status" in stats
        assert "by_gateway" in stats
        assert "total_completed_amount" in stats
        assert stats["total_payments"] >= 2

    def test_get_payments_by_date_range(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_date_1",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )

        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        payments = get_payments_by_date_range(db_session, start_date, end_date)
        assert len(payments) >= 1

    def test_get_payments_by_date_range_with_status(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_date_2",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )

        start_date = datetime.now(timezone.utc) - timedelta(days=1)
        end_date = datetime.now(timezone.utc) + timedelta(days=1)

        payments = get_payments_by_date_range(
            db_session, start_date, end_date, status=PaymentStatus.PENDING.value
        )
        assert len(payments) >= 1
