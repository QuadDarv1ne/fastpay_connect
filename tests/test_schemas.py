import pytest
from app.schemas import PaymentRequest, PaymentResponse, WebhookPayload
from pydantic import ValidationError


class TestPaymentRequest:
    def test_valid_payment_request(self):
        request = PaymentRequest(
            amount=1000.0,
            description="Оплата заказа",
        )
        assert request.amount == 1000.0
        assert request.description == "Оплата заказа"

    def test_payment_request_with_order_id(self):
        request = PaymentRequest(
            amount=500.0,
            description="Тест",
            order_id="order_123"
        )
        assert request.order_id == "order_123"

    def test_amount_zero_raises_error(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=0, description="Test")

    def test_amount_negative_raises_error(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=-100, description="Test")

    def test_amount_too_large_raises_error(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=1000001, description="Test")

    def test_empty_description_raises_error(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=100, description="")

    def test_description_whitespace_only_raises_error(self):
        with pytest.raises(ValidationError):
            PaymentRequest(amount=100, description="   ")

    def test_amount_is_rounded(self):
        request = PaymentRequest(amount=100.999, description="Test")
        assert request.amount == 101.0


class TestPaymentResponse:
    def test_valid_response(self):
        response = PaymentResponse(
            success=True,
            order_id="order_123",
            amount=1000.0,
            message="Платёж успешно создан"
        )
        assert response.success is True
        assert response.payment_id is None
        assert response.payment_url is None

    def test_response_with_payment_data(self):
        response = PaymentResponse(
            success=True,
            payment_id="pay_123",
            payment_url="https://example.com/pay",
            order_id="order_123",
            amount=1000.0,
            message="Платёж успешно создан"
        )
        assert response.payment_id == "pay_123"
        assert response.payment_url == "https://example.com/pay"


class TestWebhookPayload:
    def test_valid_payload(self):
        payload = WebhookPayload(
            status="success",
            amount=1000.0,
            currency="RUB"
        )
        assert payload.status == "success"
        assert payload.amount == 1000.0

    def test_invalid_status_raises_error(self):
        with pytest.raises(ValidationError):
            WebhookPayload(status="invalid_status")

    def test_valid_statuses(self):
        for status in ["success", "failed", "pending", "cancelled", "refunded"]:
            payload = WebhookPayload(status=status)
            assert payload.status == status
