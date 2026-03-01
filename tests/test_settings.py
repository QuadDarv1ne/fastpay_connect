import pytest
from app.utils.settings_validator import SettingsValidator


class TestSettingsValidator:
    def test_check_required_pass(self):
        validator = SettingsValidator()
        assert validator.check_required("value", "TEST_VAR") is True
        assert validator.errors == []

    def test_check_required_fail(self):
        validator = SettingsValidator()
        assert validator.check_required(None, "TEST_VAR") is False
        assert "Required setting 'TEST_VAR' is not configured" in validator.errors

    def test_check_required_empty_string(self):
        validator = SettingsValidator()
        assert validator.check_required("", "TEST_VAR") is False

    def test_validate_payment_gateway_pass(self):
        validator = SettingsValidator()
        assert (
            validator.validate_payment_gateway("Test", "api_key", "secret_key") is True
        )
        assert validator.errors == []

    def test_validate_payment_gateway_fail_no_api(self):
        validator = SettingsValidator()
        assert (
            validator.validate_payment_gateway("Test", None, "secret_key") is False
        )
        assert any("API key not configured" in e for e in validator.errors)

    def test_validate_payment_gateway_fail_no_secret(self):
        validator = SettingsValidator()
        assert (
            validator.validate_payment_gateway("Test", "api_key", None) is False
        )
        assert any("Secret key not configured" in e for e in validator.errors)

    def test_validate_all_pass(self):
        validator = SettingsValidator()
        result = validator.validate_all(
            yookassa_key="yookassa_key",
            yookassa_secret="yookassa_secret",
            tinkoff_key="tinkoff_key",
            tinkoff_secret="tinkoff_secret",
            cloudpayments_key="cp_key",
            cloudpayments_secret="cp_secret",
            unitpay_key="unitpay_key",
            unitpay_secret="unitpay_secret",
            robokassa_key="robokassa_key",
            robokassa_secret="robokassa_secret",
            secret_key="secret_key",
            database_url="sqlite:///./test.db",
        )
        assert result is True

    def test_validate_all_fail_missing_secret_key(self):
        validator = SettingsValidator()
        result = validator.validate_all(
            yookassa_key="yookassa_key",
            yookassa_secret="yookassa_secret",
            tinkoff_key="tinkoff_key",
            tinkoff_secret="tinkoff_secret",
            cloudpayments_key="cp_key",
            cloudpayments_secret="cp_secret",
            unitpay_key="unitpay_key",
            unitpay_secret="unitpay_secret",
            robokassa_key="robokassa_key",
            robokassa_secret="robokassa_secret",
            secret_key=None,
            database_url="sqlite:///./test.db",
        )
        assert result is False
        assert any("SECRET_KEY" in e for e in validator.errors)

    def test_validate_all_fail_missing_database(self):
        validator = SettingsValidator()
        result = validator.validate_all(
            yookassa_key="yookassa_key",
            yookassa_secret="yookassa_secret",
            tinkoff_key="tinkoff_key",
            tinkoff_secret="tinkoff_secret",
            cloudpayments_key="cp_key",
            cloudpayments_secret="cp_secret",
            unitpay_key="unitpay_key",
            unitpay_secret="unitpay_secret",
            robokassa_key="robokassa_key",
            robokassa_secret="robokassa_secret",
            secret_key="secret_key",
            database_url=None,
        )
        assert result is False
        assert any("DATABASE_URL" in e for e in validator.errors)
