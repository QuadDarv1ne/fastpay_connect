"""Schemas for FastPay Connect."""

from app.schemas.auth import (
    Token,
    TokenData,
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    RefreshTokenRequest,
    PasswordChange,
)

from app.schemas.payment import (
    PaymentRequest,
    PaymentResponse,
    PaymentStatusEnum,
    WebhookPayload,
    BulkPaymentRequest,
)

__all__ = [
    # Auth schemas
    "Token",
    "TokenData",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "LoginRequest",
    "RefreshTokenRequest",
    "PasswordChange",
    # Payment schemas
    "PaymentRequest",
    "PaymentResponse",
    "PaymentStatusEnum",
    "WebhookPayload",
    "BulkPaymentRequest",
]
