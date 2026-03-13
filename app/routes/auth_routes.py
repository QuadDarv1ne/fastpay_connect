"""
OAuth2 authentication routes.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
import logging

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    Token,
    LoginRequest,
    UserCreate,
    UserResponse,
    PasswordChange,
    RefreshTokenRequest,
)
from app.utils.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    get_password_hash,
    update_last_login,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.models.user import User
from app.middleware.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


def get_user_repository(db: Any = Depends(get_db)) -> UserRepository:
    """Dependency для получения UserRepository."""
    return UserRepository(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """
    Регистрация нового пользователя.
    
    Создаёт нового пользователя с указанными данными.
    """
    # Проверка сложности пароля
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )
    
    # Проверка username
    if not user_data.username.isalnum() and '_' not in user_data.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain alphanumeric characters and underscores",
        )
    
    user = repository.create(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
        roles=user_data.roles if user_data.roles else ["viewer"],
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=user.get_roles(),
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
    )


@router.post("/login", response_model=Token)
@limiter.limit("20/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """
    OAuth2 login для получения токена доступа.
    
    Используйте username и password в качестве учётных данных.
    """
    user = authenticate_user(repository.db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    # Обновление времени последнего входа
    update_last_login(repository.db, user)
    
    # Создание токенов
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.get_roles(),
        },
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id,
        },
    )
    
    logger.info(f"User '{user.username}' logged in successfully")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/login/json", response_model=Token)
@limiter.limit("20/minute")
async def login_json(
    request: Request,
    login_data: LoginRequest,
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """
    Login через JSON payload (альтернатива form-data).
    """
    user = authenticate_user(repository.db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    update_last_login(repository.db, user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.get_roles(),
        },
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id,
        },
    )
    
    logger.info(f"User '{user.username}' logged in successfully (JSON)")
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/refresh", response_model=Token)
@limiter.limit("30/hour")
async def refresh_token(
    request: Request,
    token_data: RefreshTokenRequest,
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """
    Обновление access токена с использованием refresh токена.
    """
    payload = decode_token(token_data.refresh_token, expected_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = repository.get_by_id(payload.user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создание новых токенов
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.id,
            "roles": user.get_roles(),
        },
        expires_delta=access_token_expires,
    )
    
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.username,
            "user_id": user.id,
        },
    )
    
    logger.info(f"Token refreshed for user '{user.username}'")
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/hour")
async def get_current_user_info(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Получение информации о текущем пользователе.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        roles=current_user.get_roles(),
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        last_login=current_user.last_login,
    )


@router.post("/change-password")
@limiter.limit("10/hour")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> Dict[str, str]:
    """
    Смена пароля текущего пользователя.
    """
    # Проверка старого пароля
    from app.utils.security import verify_password
    
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )
    
    # Обновление пароля
    user = repository.update(
        user=current_user,
        password=password_data.new_password,
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )
    
    logger.info(f"Password changed for user '{current_user.username}'")
    
    return {"status": "success", "message": "Password changed successfully"}


@router.post("/logout")
@limiter.limit("100/hour")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Выход из системы (на клиенте нужно удалить токены).
    """
    logger.info(f"User '{current_user.username}' logged out")
    
    return {"status": "success", "message": "Logged out successfully"}
