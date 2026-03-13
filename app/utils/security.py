"""
Security utilities for OAuth2 authentication.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Union
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import logging
import bcrypt

from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData
from app.settings import settings

logger = logging.getLogger(__name__)

# Конфигурация
SECRET_KEY = settings.secret_key or "change-me-in-production-min-32-chars!"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Хеширование пароля."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Создание access токена."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Создание refresh токена."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str, expected_type: str = "access") -> Optional[TokenData]:
    """Декодирование токена."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Проверка типа токена
        token_type = payload.get("type")
        if token_type != expected_type:
            return None
        
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        roles: List[str] = payload.get("roles", [])
        exp_timestamp = payload.get("exp")
        
        if username is None or user_id is None:
            return None
        
        exp = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else None
        
        return TokenData(
            username=username,
            user_id=user_id,
            roles=roles,
            exp=exp,
        )
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        return None


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> Optional[User]:
    """Аутентификация пользователя."""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    
    return user


def update_last_login(db: Session, user: User) -> User:
    """Обновление времени последнего входа."""
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Получение текущего пользователя из токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Пробуем получить токен из заголовка Authorization
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise credentials_exception
    
    token_data = decode_token(token, expected_type="access")
    
    if token_data is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Получение текущего суперпользователя."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


def require_role(required_role: str):
    """Декоратор для проверки роли пользователя."""
    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' is required",
            )
        return current_user
    return role_checker


def require_any_role(allowed_roles: List[str]):
    """Декоратор для проверки любой из указанных ролей."""
    async def roles_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not current_user.has_any_role(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of roles {allowed_roles} is required",
            )
        return current_user
    return roles_checker
