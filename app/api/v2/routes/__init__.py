"""API v2 routes package."""

from app.api.v2.routes import health, payments, webhooks, admin, i18n

__all__ = ["health", "payments", "webhooks", "admin", "i18n"]
