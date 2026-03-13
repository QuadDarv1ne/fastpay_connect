"""Tests for schemas and email service."""

import pytest
from pydantic import ValidationError
from app.schemas import PaymentRequest, PaymentResponse, WebhookPayload, BulkPaymentRequest, PaymentStatusEnum


class TestPaymentRequest:
    def test_valid_payment_request(self):
        req = PaymentRequest(amount=100.0, description="Test payment")
        assert req.amount == 100.0
        assert req.description == "Test payment"
        assert req.order_id is None
        assert req.email is None

    def test_payment_request_with_email(self):
        req = PaymentRequest(
            amount=100.0,
            description="Test",
            email="user@example.com"
        )
        assert req.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=100.0, description="Test", email="invalid-email")

    def test_amount_zero(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=0, description="Test")

    def test_amount_negative(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=-100, description="Test")

    def test_amount_too_large(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=1000001, description="Test")

    def test_empty_description(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=100, description="")

    def test_description_whitespace_only(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=100, description="   ")

    def test_amount_rounding(self):
        req = PaymentRequest(amount=100.12345, description="Test")
        assert req.amount == 100.12


class TestPaymentResponse:
    def test_valid_response(self):
        resp = PaymentResponse(
            success=True,
            payment_id="pay_123",
            order_id="order_123",
            amount=100.0,
            message="Success"
        )
        assert resp.success is True
        assert resp.payment_id == "pay_123"


class TestWebhookPayload:
    def test_valid_payload(self):
        payload = WebhookPayload(
            payment_id="pay_123",
            order_id="order_123",
            status=PaymentStatusEnum.COMPLETED,
            amount=100.0
        )
        assert payload.status == PaymentStatusEnum.COMPLETED

    def test_status_from_string(self):
        payload = WebhookPayload(
            payment_id="pay_123",
            status="pending"
        )
        assert payload.status == PaymentStatusEnum.PENDING

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            WebhookPayload(payment_id="pay_123", status="invalid_status")


class TestBulkPaymentRequest:
    def test_valid_bulk_request(self):
        req = BulkPaymentRequest(payments=[
            {"amount": 100.0, "description": "Payment 1"},
            {"amount": 200.0, "description": "Payment 2"}
        ])
        assert len(req.payments) == 2

    def test_empty_list(self):
        with pytest.raises(ValidationError):
            BulkPaymentRequest(payments=[])

    def test_too_many_payments(self):
        with pytest.raises(ValidationError):
            BulkPaymentRequest(payments=[
                {"amount": 100.0, "description": f"Payment {i}"}
                for i in range(101)
            ])

    def test_max_payments(self):
        req = BulkPaymentRequest(payments=[
            {"amount": 100.0, "description": f"Payment {i}"}
            for i in range(100)
        ])
        assert len(req.payments) == 100
