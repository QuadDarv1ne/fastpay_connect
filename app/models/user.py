"""
User model for OAuth2 authentication with 2FA support.
Автор: Dupley Maxim Igorevich
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(enum.Enum):
    """Роли пользователей."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """Модель пользователя для аутентификации с поддержкой 2FA."""

    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), index=True, nullable=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    roles = Column(String(255), default='["viewer"]')  # JSON список ролей
    
    # 2FA поля
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)  # Зашифрованный TOTP секрет
    mfa_backup_codes = Column(Text, nullable=True)  # JSON список backup кодов (hashed)
    mfa_last_verified = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    last_login = Column(DateTime, nullable=True)

    # Связь с tenant
    tenant = relationship("Tenant", backref="users")

    def __repr__(self) -> str:
        return f"<User(username={self.username}, email={self.email})>"

    def get_roles(self) -> List[str]:
        """Получить список ролей пользователя."""
        if not self.roles:
            return ["viewer"]
        import json
        try:
            return json.loads(self.roles)
        except (json.JSONDecodeError, TypeError):
            return [self.roles] if self.roles else ["viewer"]

    def has_role(self, role: str) -> bool:
        """Проверить наличие роли."""
        return role in self.get_roles() or self.is_superuser

    def has_any_role(self, roles: List[str]) -> bool:
        """Проверить наличие любой из указанных ролей."""
        user_roles = self.get_roles()
        return any(role in user_roles for role in roles) or self.is_superuser

    def get_backup_codes_count(self) -> int:
        """Получить количество оставшихся backup кодов."""
        if not self.mfa_backup_codes:
            return 0
        import json
        try:
            codes = json.loads(self.mfa_backup_codes)
            return len(codes) if codes else 0
        except (json.JSONDecodeError, TypeError):
            return 0
