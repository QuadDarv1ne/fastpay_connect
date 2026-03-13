"""Authentication routes for API v1."""

from fastapi import APIRouter, Depends, Request, HTTPException
from typing import Dict, Any
from datetime import timedelta

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    Token,
    UserCreate,
    UserResponse,
    LoginRequest,
    RefreshTokenRequest,
    PasswordChange,
)
from app.utils.security import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    update_last_login,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.middleware.rate_limiter import limiter
from app.models.user import User

router = APIRouter()


def get_user_repository(db: Any = Depends(get_db)) -> UserRepository:
    """Dependency для получения UserRepository."""
    return UserRepository(db)


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/hour")
async def register_v1(
    request: Request,
    user_data: UserCreate,
    repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Register a new user (v1)."""
    if len(user_data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    user = repository.create(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_active=user_data.is_active,
        is_superuser=user_data.is_superuser,
        roles=user_data.roles if user_data.roles else ["viewer"],
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
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
async def login_v1(
    request: Request,
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """Login and get access token (v1)."""
    # Получаем данные из form-data
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    
    user = authenticate_user(repository.db, username, password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    update_last_login(repository.db, user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "roles": user.get_roles()},
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id},
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/login/json", response_model=Token)
@limiter.limit("20/minute")
async def login_json_v1(
    request: Request,
    login_data: LoginRequest,
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """Login via JSON payload (v1)."""
    user = authenticate_user(repository.db, login_data.username, login_data.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    
    update_last_login(repository.db, user)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "roles": user.get_roles()},
        expires_delta=access_token_expires,
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id},
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.post("/refresh", response_model=Token)
@limiter.limit("30/hour")
async def refresh_token_v1(
    request: Request,
    token_data: RefreshTokenRequest,
    repository: UserRepository = Depends(get_user_repository),
) -> Token:
    """Refresh access token (v1)."""
    payload = decode_token(token_data.refresh_token, expected_type="refresh")
    
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = repository.get_by_id(payload.user_id)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "roles": user.get_roles()},
        expires_delta=access_token_expires,
    )
    
    new_refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id},
    )
    
    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=int(access_token_expires.total_seconds()),
    )


@router.get("/me", response_model=UserResponse)
@limiter.limit("100/hour")
async def get_current_user_info_v1(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information (v1)."""
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
async def change_password_v1(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    repository: UserRepository = Depends(get_user_repository),
) -> Dict[str, str]:
    """Change user password (v1)."""
    from app.utils.security import verify_password
    
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    user = repository.update(user=current_user, password=password_data.new_password)
    
    if not user:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    return {"status": "success", "message": "Password changed successfully"}


@router.post("/logout")
@limiter.limit("100/hour")
async def logout_v1(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Dict[str, str]:
    """Logout (v1)."""
    return {"status": "success", "message": "Logged out successfully"}
