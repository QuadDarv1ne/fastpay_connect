"""
OAuth2 authentication schemas.
"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr


class Token(BaseModel):
    """OAuth2 токен."""
    
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int = 3600


class TokenData(BaseModel):
    """Данные из токена."""
    
    username: Optional[str] = None
    user_id: Optional[int] = None
    roles: List[str] = Field(default_factory=list)
    exp: Optional[datetime] = None


class UserBase(BaseModel):
    """Базовая модель пользователя."""
    
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    roles: List[str] = Field(default_factory=list)


class UserCreate(UserBase):
    """Модель для создания пользователя."""
    
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Модель для обновления пользователя."""
    
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    roles: Optional[List[str]] = None


class UserResponse(UserBase):
    """Модель ответа с данными пользователя."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Запрос на вход."""
    
    username: str
    password: str


class RefreshTokenRequest(BaseModel):
    """Запрос на обновление токена."""
    
    refresh_token: str


class PasswordChange(BaseModel):
    """Запрос на смену пароля."""
    
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
