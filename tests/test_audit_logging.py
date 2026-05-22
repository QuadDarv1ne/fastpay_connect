"""Tests for audit logging functionality."""

import os

os.environ["APP_ENV"] = "testing"
os.environ["DISABLE_CELERY"] = "true"
os.environ["DISABLE_RATE_LIMITING"] = "true"
os.environ["DISABLE_WEBHOOK_SECURITY"] = "true"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils.security import hash_password
from app.utils.audit import log_audit_action


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///./test_audit.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


class TestAuditLogModel:
    """Test AuditLog model."""

    def test_create_audit_log(self, test_session):
        """Test creating an audit log entry."""
        entry = AuditLog(
            user_id=1,
            username="testadmin",
            action="refund",
            resource_type="payment",
            resource_id="order-123",
            details="Refund reason: customer request",
            ip_address="127.0.0.1",
        )
        test_session.add(entry)
        test_session.flush()
        test_session.commit()

        assert entry.id is not None
        assert entry.username == "testadmin"
        assert entry.action == "refund"

    def test_audit_log_to_dict(self, test_session):
        """Test audit log serialization to dict."""
        entry = AuditLog(
            user_id=1,
            username="testadmin",
            action="cancel",
            resource_type="payment",
            resource_id="order-456",
            ip_address="192.168.1.1",
        )
        test_session.add(entry)
        test_session.flush()
        test_session.commit()

        data = entry.to_dict()
        assert data["username"] == "testadmin"
        assert data["action"] == "cancel"
        assert data["resource_type"] == "payment"
        assert data["ip_address"] == "192.168.1.1"
        assert data["created_at"] is not None

    def test_audit_log_repr(self):
        """Test audit log string representation."""
        entry = AuditLog(
            id=1,
            user_id=1,
            username="admin",
            action="refund",
            resource_type="payment",
            resource_id="order-1",
        )
        assert "admin" in repr(entry)
        assert "refund" in repr(entry)


class TestAuditUtility:
    """Test audit logging utility function."""

    def test_log_audit_action(self, test_session):
        """Test logging an audit action."""
        entry = log_audit_action(
            db=test_session,
            user_id=1,
            username="admin",
            action="refund",
            resource_type="payment",
            resource_id="order-123",
            details="Test refund",
            ip_address="127.0.0.1",
        )

        assert entry.id is not None
        assert entry.user_id == 1
        assert entry.action == "refund"
        assert entry.resource_id == "order-123"

    def test_log_audit_action_minimal(self, test_session):
        """Test logging with minimal fields."""
        entry = log_audit_action(
            db=test_session,
            user_id=2,
            username="operator",
            action="cancel",
            resource_type="payment",
            resource_id="order-789",
        )

        assert entry.id is not None
        assert entry.details is None
        assert entry.ip_address is None


class TestAuditLogEndpoint:
    """Test audit log API endpoint."""

    def test_audit_logs_endpoint_exists(self):
        """Test that the audit logs endpoint is registered."""
        routes = [route.path for route in app.routes]
        # The v2 admin router is mounted under /api/v2/admin prefix
        assert any("/admin/audit-logs" in path for path in routes)
