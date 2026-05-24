"""
2FA (Two-Factor Authentication) Service with TOTP support.
Автор: Dupley Maxim Igorevich
"""

import pyotp
import base64
import json
import secrets
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from app.utils.security import verify_password


class MFAService:
    """Сервис для управления двухфакторной аутентификацией."""

    def __init__(self, issuer: str = "FastPay Connect"):
        self.issuer = issuer

    def generate_secret(self) -> str:
        """Генерация нового TOTP секрета."""
        return pyotp.random_base32()

    def get_provisioning_uri(self, secret: str, username: str, email: str) -> str:
        """Получение URI для настройки в Google Authenticator."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=self.issuer)

    def get_qr_code_url(self, secret: str, username: str, email: str) -> str:
        """Получение URL для QR кода."""
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(name=email, issuer_name=self.issuer)
        
        # Google Chart API для генерации QR кода
        chart_url = "https://chart.googleapis.com/chart"
        params = f"?chs=200x200&chld=M|0&cht=qr&chl={provisioning_uri}"
        return chart_url + params

    def verify_code(self, secret: str, code: str, window: int = 1) -> bool:
        """
        Проверка TOTP кода.
        
        Args:
            secret: TOTP секрет
            code: 6-значный код
            window: Допустимое отклонение во времени (в периодах)
        
        Returns:
            True если код верный
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """Генерация backup кодов."""
        codes = []
        for _ in range(count):
            # Генерируем код формата XXXX-YYYY
            code = f"{secrets.randbelow(10000):04d}-{secrets.randbelow(10000):04d}"
            codes.append(code)
        return codes

    def hash_backup_codes(self, codes: List[str]) -> List[str]:
        """Хеширование backup кодов для безопасного хранения."""
        from app.utils.security import get_password_hash
        return [get_password_hash(code) for code in codes]

    def verify_backup_code(self, code: str, hashed_codes: List[str]) -> bool:
        """Проверка backup кода."""
        from app.utils.security import verify_password
        for hashed_code in hashed_codes:
            if verify_password(code, hashed_code):
                return True
        return False

    def remove_used_backup_code(self, code: str, hashed_codes: List[str]) -> List[str]:
        """Удаление использованного backup кода."""
        for i, hashed_code in enumerate(hashed_codes):
            if verify_password(code, hashed_code):
                return hashed_codes[:i] + hashed_codes[i + 1:]
        return hashed_codes[:]

    def serialize_backup_codes(self, hashed_codes: List[str]) -> str:
        """Сериализация хешированных backup кодов в JSON строку."""
        return json.dumps(hashed_codes)

    def deserialize_backup_codes(self, codes_json: str) -> List[str]:
        """Десериализация JSON строки в список хешированных кодов."""
        if not codes_json:
            return []
        try:
            return json.loads(codes_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def setup_mfa(self, email: str) -> Tuple[str, str, List[str]]:
        """
        Настройка 2FA.
        
        Returns:
            (secret, qr_code_url, backup_codes)
        """
        secret = self.generate_secret()
        qr_code_url = self.get_qr_code_url(secret, email.split('@')[0], email)
        backup_codes = self.generate_backup_codes()
        
        return secret, qr_code_url, backup_codes

    def enable_mfa(
        self,
        secret: str,
        backup_codes: List[str],
        verify_code: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Включение 2FA после проверки кода.
        
        Returns:
            (success, message)
        """
        if verify_code:
            if not self.verify_code(secret, verify_code):
                return False, "Invalid verification code"
        
        return True, "2FA enabled successfully"

    def disable_mfa(
        self,
        secret: str,
        verify_code: str
    ) -> Tuple[bool, str]:
        """
        Отключение 2FA.
        
        Returns:
            (success, message)
        """
        if not self.verify_code(secret, verify_code):
            return False, "Invalid verification code"
        
        return True, "2FA disabled successfully"


# Глобальный экземпляр сервиса
mfa_service = MFAService()


def generate_totp_secret() -> str:
    """Генерация нового TOTP секрета."""
    return mfa_service.generate_secret()


def get_provisioning_uri(secret: str, username: str, email: str) -> str:
    """Получение URI для настройки в Google Authenticator."""
    return mfa_service.get_provisioning_uri(secret, username, email)


def verify_totp_code(secret: str, code: str) -> bool:
    """Проверка TOTP кода."""
    return mfa_service.verify_code(secret, code)


def generate_backup_codes(count: int = 10) -> List[str]:
    """Генерация backup кодов."""
    return mfa_service.generate_backup_codes(count)
