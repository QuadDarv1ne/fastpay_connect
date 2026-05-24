"""Audit logging utilities for admin actions."""

import logging
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_audit_action(
    db: Session,
    user_id: int,
    username: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Записать действие в audit log.

    Note: Does NOT commit. Caller must call db.commit() to ensure
    the audit entry is written atomically with related changes.
    """
    entry = AuditLog(
        user_id=user_id,
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
