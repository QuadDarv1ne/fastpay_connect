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
    PaymentErrorResponse,
    PaymentStatusEnum,
    WebhookPayload,
    BulkPaymentRequest,
    CurrencyEnum,
)

from app.schemas.webhook import (
    WebhookEventResponse,
    WebhookEventListResponse,
    WebhookStatsResponse,
    WebhookRetryRequest,
)

from app.schemas.apple_pay import (
    ApplePayPaymentRequest,
    ApplePayPaymentSessionRequest,
    ApplePayTokenRequest,
    ApplePayPaymentResponse,
    ApplePayPaymentInfoResponse,
    ApplePayRefundRequest,
    ApplePayRefundResponse,
    ApplePayWebhookPayload,
    ApplePayWebhookResponse,
    ApplePayMerchantValidationRequest,
    ApplePayMerchantValidationResponse,
    ApplePayNetworkEnum,
    ApplePayStatusEnum,
)

from app.schemas.google_pay import (
    GooglePayPaymentRequest,
    GooglePayPaymentDataRequest,
    GooglePayTokenRequest,
    GooglePayPaymentResponse,
    GooglePayPaymentInfoResponse,
    GooglePayRefundRequest,
    GooglePayRefundResponse,
    GooglePayWebhookPayload,
    GooglePayWebhookResponse,
    GooglePayMerchantValidationResponse,
    GooglePayIsReadyToPayResponse,
    GooglePayNetworkEnum,
    GooglePayCardClassEnum,
    GooglePayStatusEnum,
    GooglePayEnvironmentEnum,
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
    "PaymentErrorResponse",
    "PaymentStatusEnum",
    "WebhookPayload",
    "BulkPaymentRequest",
    "CurrencyEnum",
    # Webhook schemas
    "WebhookEventResponse",
    "WebhookEventListResponse",
    "WebhookStatsResponse",
    "WebhookRetryRequest",
    # Apple Pay schemas
    "ApplePayPaymentRequest",
    "ApplePayPaymentSessionRequest",
    "ApplePayTokenRequest",
    "ApplePayPaymentResponse",
    "ApplePayPaymentInfoResponse",
    "ApplePayRefundRequest",
    "ApplePayRefundResponse",
    "ApplePayWebhookPayload",
    "ApplePayWebhookResponse",
    "ApplePayMerchantValidationRequest",
    "ApplePayMerchantValidationResponse",
    "ApplePayNetworkEnum",
    "ApplePayStatusEnum",
    # Google Pay schemas
    "GooglePayPaymentRequest",
    "GooglePayPaymentDataRequest",
    "GooglePayTokenRequest",
    "GooglePayPaymentResponse",
    "GooglePayPaymentInfoResponse",
    "GooglePayRefundRequest",
    "GooglePayRefundResponse",
    "GooglePayWebhookPayload",
    "GooglePayWebhookResponse",
    "GooglePayMerchantValidationResponse",
    "GooglePayIsReadyToPayResponse",
    "GooglePayNetworkEnum",
    "GooglePayCardClassEnum",
    "GooglePayStatusEnum",
    "GooglePayEnvironmentEnum",
]
