"""Tests for webhook signature verification."""

import pytest
import hashlib
import hmac
from datetime import datetime, timezone, timedelta

from app.utils.webhook_signature import (
    verify_hmac_signature,
    verify_yookassa_signature,
    verify_tinkoff_signature,
    verify_cloudpayments_signature,
    verify_unitpay_signature,
    verify_robokassa_signature,
    verify_rustore_signature,
    verify_sbp_signature,
    signature_verifier,
)


class TestHMACSignatureVerification:
    """Тесты для базовой HMAC проверки."""

    def test_valid_hmac_sha256_hex(self):
        """Проверка валидной HMAC-SHA256 подписи в hex формате."""
        payload = b'{"order_id": "123", "amount": 1000}'
        secret = "test_secret_key"
        
        # Вычисляем правильную подпись
        expected = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_hmac_signature(payload, expected, secret, "sha256", "hex") is True

    def test_invalid_hmac_signature(self):
        """Проверка невалидной подписи."""
        payload = b'{"order_id": "123"}'
        secret = "test_secret"
        invalid_signature = "invalid_signature"
        
        assert verify_hmac_signature(payload, invalid_signature, secret) is False

    def test_wrong_secret_key(self):
        """Проверка с неправильным секретным ключом."""
        payload = b'{"order_id": "123"}'
        secret = "correct_secret"
        wrong_secret = "wrong_secret"
        
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        # Подпись вычислена с одним ключом, проверяем с другим
        assert verify_hmac_signature(payload, signature, wrong_secret) is False


class TestYooKassaSignature:
    """Тесты для YooKassa signature."""

    def test_valid_yookassa_signature(self):
        """Проверка валидной подписи YooKassa."""
        payload = b'{"notification_type": "paymentSucceeded"}'
        secret = "yookassa_secret"
        
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_yookassa_signature(payload, signature, secret) is True


class TestTinkoffSignature:
    """Тесты для Tinkoff signature."""

    def test_valid_tinkoff_signature(self):
        """Проверка валидной подписи Tinkoff."""
        payload = b'{"Status": "AUTHORIZED"}'
        secret = "tinkoff_secret"
        
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_tinkoff_signature(payload, signature, secret) is True


class TestCloudPaymentsSignature:
    """Тесты для CloudPayments signature."""

    def test_valid_cloudpayments_signature(self):
        """Проверка валидной подписи CloudPayments."""
        payload = b'{"TransactionId": 12345}'
        secret = "cp_secret"
        
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_cloudpayments_signature(payload, signature, secret) is True


class TestUnitPaySignature:
    """Тесты для UnitPay signature."""

    def test_valid_unitpay_signature(self):
        """Проверка валидной подписи UnitPay."""
        secret = "unitpay_secret"
        params = {
            'account': 'SHOP_ID',
            'amount': 1000,
            'order_id': 'ORDER_123',
            'purse': 'RUB',
            'command': 'pay',
            'test_mode': '0'
        }
        
        # Вычисляем правильную подпись
        hash_string = f"{params['account']}{params['amount']}{secret}{params['command']}{params['order_id']}{params['purse']}{params['test_mode']}"
        signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        assert verify_unitpay_signature(params, secret, signature) is True

    def test_invalid_unitpay_signature(self):
        """Проверка невалидной подписи UnitPay."""
        params = {'account': 'SHOP', 'amount': 1000, 'order_id': '123'}
        secret = "secret"
        invalid_signature = "invalid"
        
        assert verify_unitpay_signature(params, secret, invalid_signature) is False


class TestRoboKassaSignature:
    """Тесты для RoboKassa signature."""

    def test_valid_robokassa_result_signature(self):
        """Проверка валидной подписи RoboKassa Result."""
        secret = "robokassa_secret"
        payload = b'OutSum=1000&InvId=123'
        params = {
            'MerchantLogin': 'test_shop',
            'OutSum': '1000',
            'InvId': '123'
        }
        
        # Вычисляем правильную подпись для Result
        hash_string = f"{params['MerchantLogin']}:{params['OutSum']}:{params['InvId']}:{secret}"
        signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        assert verify_robokassa_signature(payload, params, secret, signature, is_result=True) is True


class TestRuStoreSignature:
    """Тесты для RuStore signature."""

    def test_valid_rustore_signature(self):
        """Проверка валидной подписи RuStore."""
        payload = b'{"order_id": "123", "status": "PAID"}'
        secret = "rustore_secret"
        
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_rustore_signature(payload, signature, secret) is True


class TestSBPSignature:
    """Тесты для SBP signature."""

    def test_valid_sbp_signature(self):
        """Проверка валидной подписи SBP."""
        payload = b'{"transaction_id": "123"}'
        secret = "sbp_secret"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # SBP подписывает payload + timestamp
        payload_with_timestamp = payload + timestamp.encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload_with_timestamp, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_sbp_signature(payload, signature, timestamp, secret) is True

    def test_sbp_expired_timestamp(self):
        """Проверка просроченного timestamp SBP."""
        payload = b'{"transaction_id": "123"}'
        secret = "sbp_secret"
        
        # Создаём timestamp 10 минут назад (больше tolerance)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        
        payload_with_timestamp = payload + old_timestamp.encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload_with_timestamp, 
            hashlib.sha256
        ).hexdigest()
        
        # Должно вернуть False из-за старого timestamp
        assert verify_sbp_signature(payload, signature, old_timestamp, secret) is False

    def test_sbp_valid_timestamp_tolerance(self):
        """Проверка допустимого tolerance timestamp SBP."""
        payload = b'{"transaction_id": "123"}'
        secret = "sbp_secret"
        
        # Создаём timestamp 2 минуты назад (в пределах tolerance 300s)
        recent_timestamp = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
        
        payload_with_timestamp = payload + recent_timestamp.encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload_with_timestamp, 
            hashlib.sha256
        ).hexdigest()
        
        assert verify_sbp_signature(payload, signature, recent_timestamp, secret) is True


class TestSignatureVerifier:
    """Тесты для универсального верификатора."""

    def test_verifier_yookassa(self):
        """Проверка верификатора для YooKassa."""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert signature_verifier.verify(
            'yookassa', payload, signature, secret
        ) is True

    def test_verifier_rustore(self):
        """Проверка верификатора для RuStore."""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload, 
            hashlib.sha256
        ).hexdigest()
        
        assert signature_verifier.verify(
            'rustore', payload, signature, secret
        ) is True

    def test_verifier_sbp_with_timestamp(self):
        """Проверка верификатора для SBP с timestamp."""
        payload = b'{"test": "data"}'
        secret = "test_secret"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        payload_with_timestamp = payload + timestamp.encode('utf-8')
        signature = hmac.new(
            secret.encode('utf-8'), 
            payload_with_timestamp, 
            hashlib.sha256
        ).hexdigest()
        
        assert signature_verifier.verify(
            'sbp', payload, signature, secret, timestamp=timestamp
        ) is True

    def test_verifier_unknown_gateway(self):
        """Проверка верификатора для неизвестного шлюза."""
        assert signature_verifier.verify(
            'unknown_gateway', b'payload', 'signature', 'secret'
        ) is False

    def test_verifier_missing_timestamp_for_sbp(self):
        """Проверка что SBP требует timestamp."""
        assert signature_verifier.verify(
            'sbp', b'payload', 'signature', 'secret', timestamp=None
        ) is False
