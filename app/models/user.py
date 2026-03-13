"""
User model for OAuth2 authentication.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Optional, List
from app.database import Base
import enum


class UserRole(enum.Enum):
    """Роли пользователей."""
    
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """Модель пользователя для аутентификации."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    roles = Column(String(255), default="viewer")  # JSON список ролей
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime, 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )
    last_login = Column(DateTime, nullable=True)
    
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
