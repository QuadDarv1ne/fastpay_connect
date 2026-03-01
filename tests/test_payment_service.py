import pytest
from app.services.payment_service import (
    create_payment_record,
    update_payment_status,
    get_payment_by_order_id,
    get_payment_by_id,
)
from app.models.payment import PaymentStatus


class TestCreatePaymentRecord:
    def test_create_payment(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_123",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Тестовый платёж"
        )
        assert payment.order_id == "order_123"
        assert payment.payment_gateway == "yookassa"
        assert payment.amount == 1000.0
        assert payment.status == PaymentStatus.PENDING.value
        assert payment.currency == "RUB"

    def test_create_payment_with_custom_currency(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_456",
            payment_gateway="tinkoff",
            amount=500.0,
            description="Тест",
            currency="USD"
        )
        assert payment.currency == "USD"


class TestUpdatePaymentStatus:
    def test_update_by_order_id(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_789",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Тест"
        )

        updated = update_payment_status(
            db=db_session,
            order_id="order_789",
            status=PaymentStatus.COMPLETED.value
        )

        assert updated is not None
        assert updated.status == PaymentStatus.COMPLETED.value

    def test_update_by_payment_id(self, db_session):
        payment = create_payment_record(
            db=db_session,
            order_id="order_abc",
            payment_gateway="tinkoff",
            amount=2000.0,
            description="Тест",
            payment_id="pay_abc"
        )

        updated = update_payment_status(
            db=db_session,
            payment_id="pay_abc",
            status=PaymentStatus.FAILED.value
        )

        assert updated is not None
        assert updated.status == PaymentStatus.FAILED.value

    def test_update_nonexistent_payment(self, db_session):
        updated = update_payment_status(
            db=db_session,
            order_id="nonexistent",
            status=PaymentStatus.COMPLETED.value
        )
        assert updated is None


class TestGetPayment:
    def test_get_by_order_id(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_get",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Тест"
        )

        payment = get_payment_by_order_id(db_session, "order_get")
        assert payment is not None
        assert payment.order_id == "order_get"

    def test_get_by_payment_id(self, db_session):
        create_payment_record(
            db=db_session,
            order_id="order_get2",
            payment_gateway="tinkoff",
            amount=500.0,
            description="Тест",
            payment_id="pay_get"
        )

        payment = get_payment_by_id(db_session, "pay_get")
        assert payment is not None
        assert payment.payment_id == "pay_get"

    def test_get_nonexistent(self, db_session):
        payment = get_payment_by_order_id(db_session, "nonexistent")
        assert payment is None
