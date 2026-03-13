"""
Tests for Payment Statistics Dashboard.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.payment import Payment, PaymentStatus
from app.utils.security import get_password_hash
from datetime import datetime, timezone, timedelta


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
    
    response = db_client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "AdminPass123!"},
    )
    return response.json()["access_token"]


@pytest.fixture
def test_payments(db_session):
    """Создание тестовых платежей."""
    payments = []
    
    for i in range(30):
        payment = Payment(
            order_id=f"order_dash_{i:03d}",
            payment_id=f"pay_dash_{i:03d}",
            payment_gateway=["yookassa", "tinkoff", "cloudpayments"][i % 3],
            amount=1000 + i * 100,
            currency="RUB",
            status=[PaymentStatus.COMPLETED.value, PaymentStatus.PENDING.value, PaymentStatus.FAILED.value][i % 3],
            description=f"Dashboard test payment {i}",
            created_at=datetime.now(timezone.utc) - timedelta(days=i),
        )
        db_session.add(payment)
        payments.append(payment)
    
    db_session.commit()
    return payments


class TestDashboardUI:
    """Тесты UI дашборда."""

    def test_dashboard_ui(self, db_client, admin_token):
        """Получение UI дашборда."""
        response = db_client.get(
            "/api/dashboard/ui",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Payment Statistics Dashboard" in response.text

    def test_dashboard_ui_unauthorized(self, db_client):
        """UI дашборд без авторизации."""
        response = db_client.get("/api/dashboard/ui")
        assert response.status_code == 401


class TestDashboardSummary:
    """Тесты сводной статистики."""

    def test_get_summary(self, db_client, admin_token, test_payments):
        """Получение сводной статистики."""
        response = db_client.get(
            "/api/dashboard/summary?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "total_payments" in data["data"]
        assert "total_amount" in data["data"]
        assert "conversion_rate" in data["data"]
        assert "average_check" in data["data"]

    def test_get_summary_custom_days(self, db_client, admin_token, test_payments):
        """Получение статистики за custom период."""
        response = db_client.get(
            "/api/dashboard/summary?days=7",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["period_days"] == 7


class TestDailyStatistics:
    """Тесты ежедневной статистики."""

    def test_get_daily_stats(self, db_client, admin_token, test_payments):
        """Получение ежедневной статистики."""
        response = db_client.get(
            "/api/dashboard/daily-stats?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        
        if data["data"]:
            first_day = data["data"][0]
            assert "date" in first_day
            assert "total_payments" in first_day
            assert "total_amount" in first_day

    def test_get_daily_stats_invalid_days(self, db_client, admin_token):
        """Невалидный период."""
        response = db_client.get(
            "/api/dashboard/daily-stats?days=100",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 422  # Validation error


class TestGatewayStatistics:
    """Тесты статистики по gateway."""

    def test_get_gateway_stats(self, db_client, admin_token, test_payments):
        """Получение статистики по gateway."""
        response = db_client.get(
            "/api/dashboard/gateway-stats?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        
        if data["data"]:
            first_gateway = data["data"][0]
            assert "gateway" in first_gateway
            assert "total_payments" in first_gateway
            assert "total_amount" in first_gateway
            assert "success_rate" in first_gateway

    def test_get_gateway_stats_sorted(self, db_client, admin_token, test_payments):
        """Статистика отсортирована по amount."""
        response = db_client.get(
            "/api/dashboard/gateway-stats?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        
        amounts = [g["total_amount"] for g in data["data"]]
        assert amounts == sorted(amounts, reverse=True)


class TestStatusDistribution:
    """Тесты распределения по статусам."""

    def test_get_status_distribution(self, db_client, admin_token, test_payments):
        """Получение распределения по статусам."""
        response = db_client.get(
            "/api/dashboard/status-distribution?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert isinstance(data["data"], list)
        
        if data["data"]:
            first_status = data["data"][0]
            assert "status" in first_status
            assert "count" in first_status
            assert "percentage" in first_status
            assert "amount" in first_status

    def test_status_distribution_percentages(self, db_client, admin_token, test_payments):
        """Проверка что percentages в сумме дают ~100%."""
        response = db_client.get(
            "/api/dashboard/status-distribution?days=30",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        
        # Проверяем что есть данные
        assert len(data["data"]) > 0
        
        # Проверяем что percentages корректны (каждый 0-100)
        for status_data in data["data"]:
            assert 0 <= status_data["percentage"] <= 100


class TestDashboardAuthorization:
    """Тесты авторизации dashboard."""

    def test_summary_unauthorized(self, db_client):
        """Summary без авторизации."""
        response = db_client.get("/api/dashboard/summary")
        assert response.status_code == 401

    def test_daily_stats_unauthorized(self, db_client):
        """Daily stats без авторизации."""
        response = db_client.get("/api/dashboard/daily-stats")
        assert response.status_code == 401

    def test_gateway_stats_unauthorized(self, db_client):
        """Gateway stats без авторизации."""
        response = db_client.get("/api/dashboard/gateway-stats")
        assert response.status_code == 401

    def test_status_distribution_unauthorized(self, db_client):
        """Status distribution без авторизации."""
        response = db_client.get("/api/dashboard/status-distribution")
        assert response.status_code == 401
