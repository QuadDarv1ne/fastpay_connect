"""Tests for admin dashboard endpoint."""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_payment_repository
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash
from datetime import datetime, timezone


@pytest.fixture
def db_client(db_session):
    """Test client с реальной БД сессией."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token(db_client, db_session):
    """Получение OAuth2 токена для администратора."""
    # Создаём пользователя напрямую в БД
    user = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
        roles='["admin"]',
    )
    db_session.add(user)
    db_session.commit()

    # Получаем токен
    response = db_client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "AdminPass123!"},
    )
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """Заголовки для admin endpoints с OAuth2 токеном."""
    return {"Authorization": f"Bearer {admin_token}"}


def create_mock_repository():
    """Создание мок репозитория."""
    mock_repo = MagicMock()
    mock_payment = MagicMock()
    mock_payment.order_id = "order_123"
    mock_payment.payment_id = "pay_123"
    mock_payment.payment_gateway = "yookassa"
    mock_payment.amount = 1000.0
    mock_payment.currency = "RUB"
    mock_payment.status = "pending"
    mock_payment.description = "Test"
    mock_payment.created_at = datetime.now(timezone.utc)
    mock_payment.updated_at = datetime.now(timezone.utc)
    
    mock_repo.get_dashboard_stats.return_value = {
        "total_payments": 100,
        "total_amount": 100000.0,
        "by_status": {"pending": 10, "completed": 80, "failed": 10},
        "by_gateway": {"yookassa": 50, "tinkoff": 50},
        "recent_payments": [mock_payment],
        "daily_amount": {"2024-01-01": 10000.0, "2024-01-02": 15000.0},
    }
    mock_repo.get_statistics.return_value = {
        "total_payments": 100,
        "by_status": {"pending": 10, "completed": 80, "failed": 10},
        "by_gateway": {"yookassa": 50, "tinkoff": 50},
        "total_completed_amount": 100000.0,
    }
    return mock_repo


class TestDashboardEndpoint:
    def test_get_dashboard(self, db_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get("/admin/payments/dashboard", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_payments"] == 100
        assert data["total_amount"] == 100000.0
        assert "by_status" in data
        assert "by_gateway" in data
        assert "recent_payments" in data
        assert "daily_amount" in data

        app.dependency_overrides.clear()

    def test_get_dashboard_with_limit(self, db_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get(
            "/admin/payments/dashboard?limit=20",
            headers=admin_headers
        )

        assert response.status_code == 200
        mock_repo.get_dashboard_stats.assert_called_once_with(20)

        app.dependency_overrides.clear()

    def test_get_dashboard_invalid_limit(self, db_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get(
            "/admin/payments/dashboard?limit=100",
            headers=admin_headers
        )

        assert response.status_code == 422

        app.dependency_overrides.clear()

    def test_get_dashboard_no_api_key(self, db_client):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get("/admin/payments/dashboard")

        assert response.status_code == 401

        app.dependency_overrides.clear()

    def test_get_dashboard_invalid_api_key(self, db_client):
        """Тест проверяет что невалидный токен возвращает 401."""
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get(
            "/admin/payments/dashboard",
            headers={"Authorization": "Bearer invalid_token"}
        )

        # OAuth2 возвращает 401 для невалидного токена
        assert response.status_code == 401

        app.dependency_overrides.clear()


class TestStatisticsEndpoint:
    def test_get_statistics(self, db_client, admin_headers):
        mock_repo = create_mock_repository()
        app.dependency_overrides[get_payment_repository] = lambda: mock_repo

        response = db_client.get("/admin/payments/statistics", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_payments"] == 100
        assert "by_status" in data
        assert "by_gateway" in data

        app.dependency_overrides.clear()
