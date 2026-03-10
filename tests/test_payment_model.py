import pytest
from app.models.payment import Payment, PaymentStatus
from datetime import datetime, timezone


class TestPaymentModel:
    def test_payment_repr(self, db_session):
        from app.services.payment_service import create_payment_record
        
        payment = create_payment_record(
            db=db_session,
            order_id="order_repr",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test",
        )
        
        repr_str = repr(payment)
        assert "order_repr" in repr_str
        assert "1000.0" in repr_str

    def test_payment_to_dict(self, db_session):
        from app.services.payment_service import create_payment_record
        
        payment = create_payment_record(
            db=db_session,
            order_id="order_dict",
            payment_gateway="yookassa",
            amount=1000.0,
            description="Test dict",
        )
        
        result = payment.to_dict()
        
        assert result["order_id"] == "order_dict"
        assert result["payment_gateway"] == "yookassa"
        assert result["amount"] == 1000.0
        assert result["currency"] == "RUB"
        assert result["status"] == "pending"
        assert result["description"] == "Test dict"
        assert "created_at" in result
        assert "updated_at" in result

    def test_payment_to_dict_with_metadata(self, db_session):
        from app.services.payment_service import create_payment_record, update_payment_status
        
        payment = create_payment_record(
            db=db_session,
            order_id="order_meta",
            payment_gateway="tinkoff",
            amount=500.0,
            description="Test metadata",
        )
        
        update_payment_status(
            db=db_session,
            order_id="order_meta",
            status="completed",
            metadata={"transaction_id": "tx_123"},
        )
        
        result = payment.to_dict()
        
        assert result["metadata"] is not None
        assert result["metadata"]["transaction_id"] == "tx_123"

    def test_payment_status_enum_values(self):
        assert PaymentStatus.PENDING.value == "pending"
        assert PaymentStatus.PROCESSING.value == "processing"
        assert PaymentStatus.COMPLETED.value == "completed"
        assert PaymentStatus.FAILED.value == "failed"
        assert PaymentStatus.CANCELLED.value == "cancelled"
        assert PaymentStatus.REFUNDED.value == "refunded"

    def test_payment_status_enum_membership(self):
        assert str(PaymentStatus.PENDING) == "PaymentStatus.PENDING"
        assert PaymentStatus("pending") == PaymentStatus.PENDING
        assert PaymentStatus("completed") == PaymentStatus.COMPLETED
