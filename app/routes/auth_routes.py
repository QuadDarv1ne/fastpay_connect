"""
OAuth2 authentication routes.
"""

import logging
from datetime import timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from app.database import get_db
from app.middleware.rate_limiter import limiter
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (LoginRequest, PasswordChange,
                              RefreshTokenRequest, Token, UserCreate,
                              UserResponse)
from app.services.mfa_service import mfa_service
from app.utils.security import (ACCESS_TOKEN_EXPIRE_MINUTES,
                                REFRESH_TOKEN_EXPIRE_DAYS, authenticate_user,
                                create_access_token, create_refresh_token,
                                decode_token, get_current_user,
                                get_password_hash, update_last_login)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


def get_user_repository(db: Any = Depends(get_db)) -> UserRepository:
    """Dependency for UserRepository."""
    return UserRepository(db)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    repository: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Register a new user."""
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long",
        )

    if not user_data.username.isalnum() and '_' not in user_data.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username can only contain alphanumeric characters and underscores",
        )

    user = repository.create(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_active=True,
        is_superuser=False,
        roles=["viewer"],
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
    """OAuth2 login for access token."""
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

    # OAuth2 form login does not support MFA code; reject if MFA is enabled
    if user.mfa_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA required. Use /login/json with mfa_code parameter.",
            headers={"WWW-Authenticate": "Bearer"},
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
    """Login via JSON payload with MFA support."""
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

    # MFA verification
    if user.mfa_enabled:
        if not login_data.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required",
            )

        if not user.mfa_secret:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MFA misconfigured. Contact administrator.",
            )

        # Try TOTP code first
        if not mfa_service.verify_code(user.mfa_secret, login_data.mfa_code):
            # Try backup codes
            backup_codes = mfa_service.deserialize_backup_codes(user.mfa_backup_codes)
            if not mfa_service.verify_backup_code(login_data.mfa_code, backup_codes):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid MFA code",
                )
            # Remove used backup code
            new_backup_codes = mfa_service.remove_used_backup_code(
                login_data.mfa_code, backup_codes
            )
            user.mfa_backup_codes = mfa_service.serialize_backup_codes(new_backup_codes)
            try:
                repository.db.commit()
            except Exception as e:
                repository.db.rollback()
                logger.error(f"Failed to commit MFA backup code update: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update MFA backup codes",
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
    """Refresh access token using a refresh token."""
    from app.utils.token_blacklist import blacklist_token, is_token_blacklisted

    if is_token_blacklisted(token_data.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    # Only blacklist after all validations pass — prevents permanent lockout
    # when user lookup fails (e.g. DB issue) but token is already blacklisted
    success = blacklist_token(token_data.refresh_token)
    if not success:
        logger.warning("Failed to blacklist used refresh token (Redis may be unavailable)")

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
    """Get current user info."""
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
    """Change current user password."""
    from app.utils.security import verify_password

    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )

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
    """Logout with token invalidation via Redis blacklist."""
    from app.utils.token_blacklist import blacklist_token

    logger.info(f"User '{current_user.username}' logged out")

    auth_header = request.headers.get("Authorization", "")
    token = None
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]

    if token:
        success = blacklist_token(token)
        if not success:
            logger.warning("Failed to blacklist token during logout (Redis may be unavailable)")

    return {"status": "success", "message": "Logged out successfully"}
