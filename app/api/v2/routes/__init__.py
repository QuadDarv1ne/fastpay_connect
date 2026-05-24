"""API v2 routes package."""

from app.api.v2.routes import admin, health, i18n, payments, webhooks

__all__ = ["health", "payments", "webhooks", "admin", "i18n"]
