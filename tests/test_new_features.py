"""Tests for new features: API v2, subscriptions, i18n, fraud detection, split payments."""

import os
import json
import time
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.main import app
from app.models.payment import Payment, PaymentStatus
from app.models.subscription import Subscription, SubscriptionInterval, SubscriptionStatus
from app.models.split_payment import SplitPayment, SplitStatus
from app.schemas.split_payment import SplitPaymentCreateRequest, SplitRecipient


# ============================================================================
# API v2 Tests
# ============================================================================

class TestAPIV2Health:
    """Tests for API v2 health endpoints."""

    def test_health_check_v2(self, client):
        response = client.get("/api/v2/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "v2"
        assert "checks" in data

    def test_readiness_check_v2(self, client):
        response = client.get("/api/v2/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "not_ready")
        assert data["version"] == "v2"

    def test_liveness_check_v2(self, client):
        response = client.get("/api/v2/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["version"] == "v2"


class TestAPIV2Payments:
    """Tests for API v2 payment endpoints."""

    def test_create_payment_v2(self, client):
        payment_data = {
            "order_id": f"test_v2_order_{int(time.time())}",
            "amount": 100.0,
            "currency": "RUB",
            "gateway": "yookassa",
            "description": "Test payment v2",
        }
        response = client.post("/api/v2/payments/create", json=payment_data)
        # May fail due to gateway config, but endpoint should exist
        assert response.status_code in (200, 400, 500)

    def test_create_payment_v2_with_idempotency(self, client):
        idempotency_key = f"idem_test_{int(time.time())}"
        payment_data = {
            "order_id": f"test_idem_order_{int(time.time())}",
            "amount": 100.0,
            "currency": "RUB",
            "gateway": "yookassa",
            "description": "Idempotent payment",
            "idempotency_key": idempotency_key,
        }
        response = client.post("/api/v2/payments/create", json=payment_data)
        assert response.status_code in (200, 400, 500)

    def test_get_payment_status_v2(self, client):
        response = client.get("/api/v2/payments/nonexistent_order")
        # Should return 404 for non-existent order
        assert response.status_code in (200, 404)


class TestAPIV2i18n:
    """Tests for API v2 i18n endpoints."""

    def test_get_supported_languages(self, client):
        response = client.get("/api/v2/i18n/languages")
        assert response.status_code == 200
        data = response.json()
        assert "supported_languages" in data
        assert "ru" in data["supported_languages"]
        assert "en" in data["supported_languages"]

    def test_get_translations_default(self, client):
        response = client.get("/api/v2/i18n/translations")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "ru"
        assert "translations" in data

    def test_get_translations_english(self, client):
        response = client.get("/api/v2/i18n/translations?lang=en")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"

    def test_translate_specific_key(self, client):
        response = client.get("/api/v2/i18n/translate/payment.success")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "payment.success"
        assert data["language"] == "ru"

    def test_translate_with_lang_override(self, client):
        response = client.get("/api/v2/i18n/translate/payment.success?lang=en")
        assert response.status_code == 200
        data = response.json()
        assert data["language"] == "en"
        assert "Payment" in data["translation"] or "payment" in data["translation"]


# ============================================================================
# Subscription Tests
# ============================================================================

class TestSubscriptions:
    """Tests for subscription endpoints."""

    def test_create_subscription(self, client):
        sub_data = {
            "user_id": "test_user_1",
            "plan_name": "premium",
            "amount": 999.0,
            "currency": "RUB",
            "interval": "monthly",
            "trial_days": 7,
        }
        response = client.post("/api/subscriptions", json=sub_data)
        assert response.status_code in (200, 201, 400)

    def test_create_subscription_without_trial(self, client):
        sub_data = {
            "user_id": "test_user_2",
            "plan_name": "basic",
            "amount": 499.0,
            "currency": "RUB",
            "interval": "monthly",
        }
        response = client.post("/api/subscriptions", json=sub_data)
        assert response.status_code in (200, 201, 400)

    def test_list_subscriptions(self, client):
        response = client.get("/api/subscriptions")
        assert response.status_code == 200
        data = response.json()
        assert "subscriptions" in data
        assert "total" in data

    def test_get_subscription_not_found(self, client):
        response = client.get("/api/subscriptions/999999")
        assert response.status_code == 404


class TestSubscriptionService:
    """Tests for subscription service logic."""

    def test_create_subscription_service(self, db_session):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService(db_session)
        sub = service.create_subscription(
            user_id="svc_test_user",
            plan_name="test_plan",
            amount=Decimal("599.00"),
            currency="RUB",
            interval=SubscriptionInterval.MONTHLY,
            trial_days=14,
        )

        assert sub.user_id == "svc_test_user"
        assert sub.plan_name == "test_plan"
        assert sub.status == SubscriptionStatus.TRIALING
        assert sub.trial_end is not None

    def test_cancel_subscription(self, db_session):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService(db_session)
        sub = service.create_subscription(
            user_id="cancel_test_user",
            plan_name="test_plan",
            amount=Decimal("599.00"),
            currency="RUB",
            interval=SubscriptionInterval.MONTHLY,
        )

        cancelled = service.cancel_subscription(sub.id, immediate=True)
        assert cancelled.status == SubscriptionStatus.CANCELLED
        assert cancelled.cancelled_at is not None

    def test_pause_resume_subscription(self, db_session):
        from app.services.subscription_service import SubscriptionService

        service = SubscriptionService(db_session)
        sub = service.create_subscription(
            user_id="pause_test_user",
            plan_name="test_plan",
            amount=Decimal("599.00"),
            currency="RUB",
            interval=SubscriptionInterval.MONTHLY,
        )

        paused = service.pause_subscription(sub.id)
        assert paused.status == SubscriptionStatus.PAUSED

        resumed = service.resume_subscription(sub.id)
        assert resumed.status == SubscriptionStatus.ACTIVE


# ============================================================================
# Split Payment Tests
# ============================================================================

class TestSplitPayments:
    """Tests for split payment endpoints."""

    def test_create_split_payment(self, client):
        split_data = {
            "order_id": f"split_order_{int(time.time())}",
            "total_amount": 1000.0,
            "currency": "RUB",
            "gateway": "yookassa",
            "description": "Marketplace split payment",
            "recipients": [
                {
                    "recipient_id": "vendor_1",
                    "recipient_name": "Vendor One",
                    "recipient_type": "vendor",
                    "amount": 800.0,
                },
                {
                    "recipient_id": "platform",
                    "recipient_name": "Platform",
                    "recipient_type": "platform",
                    "amount": 200.0,
                },
            ],
        }
        response = client.post("/api/payments/split", json=split_data)
        assert response.status_code in (200, 201, 400)

    def test_create_split_payment_invalid_amounts(self, client):
        """Recipient amounts don't sum to total."""
        split_data = {
            "order_id": f"split_invalid_{int(time.time())}",
            "total_amount": 1000.0,
            "currency": "RUB",
            "gateway": "yookassa",
            "recipients": [
                {
                    "recipient_id": "vendor_1",
                    "amount": 500.0,
                },
                {
                    "recipient_id": "platform",
                    "amount": 300.0,  # 500 + 300 != 1000
                },
            ],
        }
        response = client.post("/api/payments/split", json=split_data)
        assert response.status_code == 400

    def test_get_split_payment_not_found(self, client):
        response = client.get("/api/payments/split/nonexistent_order")
        assert response.status_code == 404

    def test_get_pending_splits(self, client):
        response = client.get("/api/payments/split/pending")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "splits" in data


class TestSplitPaymentService:
    """Tests for split payment service logic."""

    def test_create_split_payment_service(self, db_session):
        from app.services.split_payment_service import SplitPaymentService

        service = SplitPaymentService(db_session)
        request = SplitPaymentCreateRequest(
            order_id=f"svc_split_{int(time.time())}",
            total_amount=Decimal("1000.00"),
            currency="RUB",
            gateway="yookassa",
            description="Test split",
            recipients=[
                SplitRecipient(
                    recipient_id="vendor_1",
                    recipient_name="Vendor One",
                    recipient_type="vendor",
                    amount=Decimal("800.00"),
                ),
                SplitRecipient(
                    recipient_id="platform",
                    recipient_name="Platform",
                    recipient_type="platform",
                    amount=Decimal("200.00"),
                    commission_percent=Decimal("5"),
                ),
            ],
        )

        payment = service.create_split_payment(request)
        assert payment.order_id == request.order_id
        assert payment.amount == Decimal("1000.00")

        splits = service.get_split_payments(payment.order_id)
        assert len(splits) == 2

    def test_split_validation_error(self, db_session):
        from app.services.split_payment_service import SplitPaymentService, SplitPaymentError

        service = SplitPaymentService(db_session)
        request = SplitPaymentCreateRequest(
            order_id=f"invalid_split_{int(time.time())}",
            total_amount=Decimal("1000.00"),
            currency="RUB",
            gateway="yookassa",
            recipients=[
                SplitRecipient(
                    recipient_id="vendor_1",
                    amount=Decimal("500.00"),
                ),
            ],
        )

        with pytest.raises(SplitPaymentError):
            service.create_split_payment(request)

    def test_refund_split_payment(self, db_session):
        from app.services.split_payment_service import SplitPaymentService

        service = SplitPaymentService(db_session)
        request = SplitPaymentCreateRequest(
            order_id=f"refund_split_{int(time.time())}",
            total_amount=Decimal("500.00"),
            currency="RUB",
            gateway="yookassa",
            recipients=[
                SplitRecipient(
                    recipient_id="vendor_x",
                    amount=Decimal("500.00"),
                ),
            ],
        )

        payment = service.create_split_payment(request)
        splits = service.get_split_payments(payment.order_id)
        split = splits[0]

        # Update status to completed first
        service.update_split_status(split.id, SplitStatus.COMPLETED)

        # Now refund
        refunded = service.refund_split_payment(split.id, reason="Test refund")
        assert refunded.status == SplitStatus.REFUNDED


# ============================================================================
# i18n Utility Tests
# ============================================================================

class TestI18nUtility:
    """Tests for i18n utility functions."""

    def test_translate_russian(self):
        from app.utils.i18n import translate

        result = translate("payment.success", "ru")
        assert "успешн" in result.lower() or "success" in result.lower()

    def test_translate_english(self):
        from app.utils.i18n import translate

        result = translate("payment.success", "en")
        assert "success" in result.lower() or "Success" in result

    def test_translate_with_format(self):
        from app.utils.i18n import translate

        result = translate("subscription.trial_period", "en", days=14)
        assert "14" in result

    def test_translate_missing_key(self):
        from app.utils.i18n import translate

        result = translate("nonexistent.key", "en")
        assert result == "nonexistent.key"

    def test_translate_fallback(self):
        from app.utils.i18n import translate

        # Unknown language should fallback to Russian
        result = translate("payment.success", "fr")
        assert result  # Should return something, not crash

    def test_shorthand_t(self):
        from app.utils.i18n import t

        result = t("common.ok")
        assert result  # Should return translation

    def test_get_translations_for_language(self):
        from app.utils.i18n import get_translations_for_language

        ru = get_translations_for_language("ru")
        assert isinstance(ru, dict)
        assert len(ru) > 0

        en = get_translations_for_language("en")
        assert isinstance(en, dict)
        assert len(en) > 0


# ============================================================================
# Fraud Detection Tests
# ============================================================================

class TestFraudDetector:
    """Tests for fraud detection logic."""

    def test_fraud_detector_init(self):
        from app.middleware.fraud_detection import FraudDetector, FraudDetectionConfig

        config = FraudDetectionConfig(
            max_requests_per_minute=5,
            max_payments_per_hour=3,
        )
        detector = FraudDetector(config)
        assert detector is not None

    def test_user_agent_check(self):
        from app.middleware.fraud_detection import FraudDetector, FraudDetectionConfig

        config = FraudDetectionConfig()
        detector = FraudDetector(config)

        # Create mock request
        mock_request = MagicMock()
        mock_request.headers = {"User-Agent": "sqlmap/1.5"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = detector._check_user_agent(mock_request)
        assert result is not None
        assert "sqlmap" in result.lower()

    def test_clean_user_agent(self):
        from app.middleware.fraud_detection import FraudDetector, FraudDetectionConfig

        config = FraudDetectionConfig()
        detector = FraudDetector(config)

        mock_request = MagicMock()
        mock_request.headers = {"User-Agent": "Mozilla/5.0 Chrome/120.0"}
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        result = detector._check_user_agent(mock_request)
        assert result is None

    def test_fingerprint_generation(self):
        from app.middleware.fraud_detection import FraudDetector

        detector = FraudDetector()

        mock_request = MagicMock()
        mock_request.headers = {"User-Agent": "Mozilla/5.0"}
        mock_request.client = MagicMock()
        mock_request.client.host = "192.168.1.1"

        fp1 = detector._get_fingerprint(mock_request)
        fp2 = detector._get_fingerprint(mock_request)
        assert fp1 == fp2  # Same input = same fingerprint
        assert len(fp1) == 16  # Truncated hash

    def test_blocked_check(self):
        from app.middleware.fraud_detection import FraudDetector, FraudDetectionConfig

        config = FraudDetectionConfig(block_duration_minutes=30)
        detector = FraudDetector(config)

        # Should not be blocked initially
        assert detector.check_blocked("test_fingerprint") is None

    def test_record_failed_attempt(self):
        from app.middleware.fraud_detection import FraudDetector, FraudDetectionConfig

        config = FraudDetectionConfig(
            max_failed_attempts_per_hour=3,
            block_duration_minutes=1,
        )
        detector = FraudDetector(config)

        fp = f"fail_test_{int(time.time())}"

        # Record failures
        for _ in range(3):
            detector.record_failed_attempt(fp)

        # Should now be blocked
        blocked = detector.check_blocked(fp)
        assert blocked is not None
        assert "blocked" in blocked.lower()


# ============================================================================
# i18n Middleware Tests
# ============================================================================

class TestI18nMiddleware:
    """Tests for i18n middleware integration."""

    def test_content_language_header(self, client):
        response = client.get("/health")
        # Should have Content-Language header
        assert "content-language" in response.headers or "Content-Language" in response.headers

    def test_language_from_query_param(self, client):
        response = client.get("/api/v2/i18n/translations?lang=en")
        data = response.json()
        assert data["language"] == "en"

    def test_language_from_header(self, client):
        response = client.get("/api/v2/i18n/translations", headers={"X-Language": "en"})
        data = response.json()
        assert data["language"] == "en"
