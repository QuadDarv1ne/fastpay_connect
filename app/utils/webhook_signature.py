"""Webhook signature verification utilities.

Проверка подписей webhook уведомлений от платёжных шлюзов.
"""

import hashlib
import hmac
import logging
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
    algorithm: str = "sha256",
    header_format: str = "hex",
) -> bool:
    """Проверка HMAC подписи.

    Args:
        payload: Тело запроса (bytes)
        signature: Подпись из заголовка
        secret_key: Секретный ключ шлюза
        algorithm: Хэш-алгоритм (sha256, sha512)
        header_format: Формат подписи (hex, base64)

    Returns:
        True если подпись валидна
    """
    try:
        secret_bytes = secret_key.encode('utf-8')
        
        if algorithm == "sha256":
            computed = hmac.new(secret_bytes, payload, hashlib.sha256)
        elif algorithm == "sha512":
            computed = hmac.new(secret_bytes, payload, hashlib.sha512)
        else:
            logger.error(f"Unsupported algorithm: {algorithm}")
            return False
        
        if header_format == "hex":
            computed_signature = computed.hexdigest()
        else:
            import base64
            computed_signature = base64.b64encode(computed.digest()).decode('utf-8')
        
        # Constant-time comparison для защиты от timing attacks
        return hmac.compare_digest(computed_signature, signature.lower())
    
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def verify_yookassa_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
) -> bool:
    """Проверка подписи YooKassa.

    YooKassa использует HMAC-SHA256 с secret key.
    """
    return verify_hmac_signature(payload, signature, secret_key, "sha256", "hex")


def verify_tinkoff_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
) -> bool:
    """Проверка подписи Tinkoff.

    Tinkoff использует HMAC-SHA256 с secret key.
    """
    return verify_hmac_signature(payload, signature, secret_key, "sha256", "hex")


def verify_cloudpayments_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
) -> bool:
    """Проверка подписи CloudPayments.

    CloudPayments использует HMAC-SHA256.
    """
    return verify_hmac_signature(payload, signature, secret_key, "sha256", "hex")


def verify_unitpay_signature(
    params: Dict[str, Any],
    secret_key: str,
    signature: str,
) -> bool:
    """Проверка подписи UnitPay.

    UnitPay использует MD5 хэш от параметров + secret key.
    Формат: md5(account + amount + secret + command + order_id + purse + test_mode)
    """
    try:
        # Сортируем параметры для консистентности
        account = str(params.get('account', ''))
        amount = str(params.get('amount', ''))
        order_id = str(params.get('order_id', ''))
        purse = str(params.get('purse', ''))
        command = str(params.get('command', ''))
        test_mode = str(params.get('test_mode', ''))
        
        # Формируем строку для хэширования
        hash_string = f"{account}{amount}{secret_key}{command}{order_id}{purse}{test_mode}"
        
        computed_signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        return hmac.compare_digest(computed_signature.lower(), signature.lower())
    
    except Exception as e:
        logger.error(f"UnitPay signature verification error: {e}")
        return False


def verify_robokassa_signature(
    payload: bytes,
    params: Dict[str, Any],
    secret_key: str,
    signature: str,
    is_result: bool = True,
) -> bool:
    """Проверка подписи RoboKassa.

    RoboKassa использует MD5 хэш.
    Для Result: md5(MerchantLogin:Amount:OrderID:Password1)
    """
    try:
        merchant_login = str(params.get('MerchantLogin', ''))
        amount = str(params.get('OutSum', ''))
        order_id = str(params.get('InvId', ''))
        
        if is_result:
            hash_string = f"{merchant_login}:{amount}:{order_id}:{secret_key}"
        else:
            hash_string = f"{amount}:{order_id}:{secret_key}"
        
        computed_signature = hashlib.md5(hash_string.encode('utf-8')).hexdigest()
        
        return hmac.compare_digest(computed_signature.lower(), signature.lower())
    
    except Exception as e:
        logger.error(f"RoboKassa signature verification error: {e}")
        return False


def verify_rustore_signature(
    payload: bytes,
    signature: str,
    secret_key: str,
) -> bool:
    """Проверка подписи RuStore.

    RuStore использует HMAC-SHA256.
    Подпись в заголовке X-Signature.
    """
    return verify_hmac_signature(payload, signature, secret_key, "sha256", "hex")


def verify_sbp_signature(
    payload: bytes,
    signature: str,
    timestamp: str,
    secret_key: str,
    timestamp_tolerance_seconds: int = 300,
) -> bool:
    """Проверка подписи SBP.

    SBP использует HMAC-SHA256 с timestamp для защиты от replay attacks.
    Подпись вычисляется от: payload + timestamp
    """
    try:
        # Проверяем timestamp (защита от replay attacks)
        try:
            ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            time_diff = abs((now - ts).total_seconds())
            
            if time_diff > timestamp_tolerance_seconds:
                logger.warning(
                    f"SBP webhook timestamp too old: {time_diff}s (max: {timestamp_tolerance_seconds}s)"
                )
                return False
        except Exception as e:
            logger.error(f"SBP timestamp parsing error: {e}")
            return False
        
        # Проверяем подпись
        # SBP подписывает: payload + timestamp
        payload_with_timestamp = payload + timestamp.encode('utf-8')
        return verify_hmac_signature(
            payload_with_timestamp, 
            signature, 
            secret_key, 
            "sha256", 
            "hex"
        )
    
    except Exception as e:
        logger.error(f"SBP signature verification error: {e}")
        return False


class WebhookSignatureVerifier:
    """Универсальный верификатор подписей webhook."""

    def __init__(self):
        self.verifiers = {
            'yookassa': verify_yookassa_signature,
            'tinkoff': verify_tinkoff_signature,
            'cloudpayments': verify_cloudpayments_signature,
            'unitpay': verify_unitpay_signature,
            'robokassa': verify_robokassa_signature,
            'rustore': verify_rustore_signature,
            'sbp': verify_sbp_signature,
        }

    def verify(
        self,
        gateway: str,
        payload: bytes,
        signature: str,
        secret_key: str,
        params: Optional[Dict[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> bool:
        """Проверить подпись webhook.

        Args:
            gateway: Название шлюза
            payload: Тело запроса (bytes)
            signature: Подпись из заголовка
            secret_key: Секретный ключ
            params: Дополнительные параметры (для UnitPay, RoboKassa)
            timestamp: Timestamp (для SBP)

        Returns:
            True если подпись валидна
        """
        verifier = self.verifiers.get(gateway)
        if not verifier:
            logger.warning(f"No verifier configured for gateway: {gateway}")
            return False

        try:
            if gateway in ('unitpay', 'robokassa'):
                return verifier(payload, params or {}, secret_key, signature)
            elif gateway == 'sbp':
                if not timestamp:
                    logger.error("SBP webhook requires timestamp")
                    return False
                return verifier(payload, signature, timestamp, secret_key)
            else:
                return verifier(payload, signature, secret_key)
        
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False


# Глобальный экземпляр
signature_verifier = WebhookSignatureVerifier()
