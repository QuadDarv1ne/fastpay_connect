"""
Tests for webhook monitoring dashboard.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookEventStatus
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
def webhook_events(db_session):
    """Создание тестовых webhook событий."""
    events = []
    
    # Успешные события
    for i in range(5):
        event = WebhookEvent(
            event_id=f"event_success_{i}",
            order_id=f"order_{i}",
            gateway="yookassa",
            status=WebhookEventStatus.SUCCESS,
            retry_count=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=i),
            processed_at=datetime.now(timezone.utc),
        )
        db_session.add(event)
        events.append(event)
    
    # События в retry
    for i in range(3):
        event = WebhookEvent(
            event_id=f"event_retry_{i}",
            order_id=f"order_retry_{i}",
            gateway="tinkoff",
            status=WebhookEventStatus.RETRY,
            retry_count=i + 1,
            max_retries=5,
            last_error=f"Error {i}",
            next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=i * 10),
            created_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        db_session.add(event)
        events.append(event)
    
    # Failed события
    for i in range(2):
        event = WebhookEvent(
            event_id=f"event_failed_{i}",
            order_id=f"order_failed_{i}",
            gateway="cloudpayments",
            status=WebhookEventStatus.FAILED,
            retry_count=5,
            max_retries=5,
            last_error="Max retries exceeded",
            created_at=datetime.now(timezone.utc) - timedelta(days=i + 10),
        )
        db_session.add(event)
        events.append(event)
    
    db_session.commit()
    return events


class TestWebhookMonitoringOverview:
    """Тесты endpoint overview."""

    def test_get_overview(self, db_client, admin_token, webhook_events):
        """Получение общей статистики."""
        response = db_client.get(
            "/api/monitoring/webhooks/overview?days=7",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "total" in data["data"]
        assert "by_status" in data["data"]

    def test_get_overview_unauthorized(self, db_client):
        """Доступ без авторизации."""
        response = db_client.get("/api/monitoring/webhooks/overview")
        assert response.status_code == 401

    def test_get_overview_invalid_token(self, db_client):
        """Доступ с невалидным токеном."""
        response = db_client.get(
            "/api/monitoring/webhooks/overview",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestWebhookMonitoringDashboard:
    """Тесты endpoint dashboard."""

    def test_get_dashboard(self, db_client, admin_token, webhook_events):
        """Получение расширенной статистики."""
        response = db_client.get(
            "/api/monitoring/webhooks/dashboard?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "recent_events" in data["data"]
        assert len(data["data"]["recent_events"]) <= 10

    def test_get_dashboard_custom_limit(self, db_client, admin_token, webhook_events):
        """Получение статистики с custom limit."""
        response = db_client.get(
            "/api/monitoring/webhooks/dashboard?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["recent_events"]) <= 5


class TestWebhookMonitoringEvents:
    """Тесты endpoint events."""

    def test_get_events(self, db_client, admin_token, webhook_events):
        """Получение списка событий."""
        response = db_client.get(
            "/api/monitoring/webhooks/events?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "pages" in data["data"]

    def test_get_events_filter_by_gateway(self, db_client, admin_token, webhook_events):
        """Фильтрация по gateway."""
        response = db_client.get(
            "/api/monitoring/webhooks/events?gateway=yookassa",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]["items"]:
            assert item["gateway"] == "yookassa"

    def test_get_events_filter_by_status(self, db_client, admin_token, webhook_events):
        """Фильтрация по status."""
        response = db_client.get(
            "/api/monitoring/webhooks/events?status=retry",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["data"]["items"]:
            assert item["status"] == "retry"


class TestWebhookMonitoringEventDetail:
    """Тесты endpoint event detail."""

    def test_get_event(self, db_client, admin_token, webhook_events):
        """Получение информации о событии."""
        event = webhook_events[0]
        response = db_client.get(
            f"/api/monitoring/webhooks/events/{event.event_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["event_id"] == event.event_id

    def test_get_event_not_found(self, db_client, admin_token):
        """Событие не найдено."""
        response = db_client.get(
            "/api/monitoring/webhooks/events/nonexistent",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 404


class TestWebhookMonitoringRetryQueue:
    """Тесты endpoint retry queue."""

    def test_get_retry_queue(self, db_client, admin_token, webhook_events):
        """Получение очереди retry."""
        response = db_client.get(
            "/api/monitoring/webhooks/retry-queue?limit=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "count" in data["data"]
        assert "items" in data["data"]

    def test_get_retry_queue_empty(self, db_client, admin_token, db_session):
        """Пустая очередь retry."""
        # Очищаем все события
        db_session.query(WebhookEvent).delete()
        db_session.commit()
        
        response = db_client.get(
            "/api/monitoring/webhooks/retry-queue",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["count"] == 0


class TestWebhookMonitoringMetrics:
    """Тесты endpoint metrics."""

    def test_get_metrics(self, db_client, admin_token, webhook_events):
        """Получение метрик."""
        response = db_client.get(
            "/api/monitoring/webhooks/metrics",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "total_webhooks_24h" in data["data"]
        assert "by_gateway" in data["data"]
        assert "by_status" in data["data"]


class TestWebhookMonitoringUI:
    """Тесты UI dashboard."""

    def test_get_dashboard_ui(self, db_client, admin_token):
        """Получение UI дашборда."""
        response = db_client.get(
            "/api/monitoring/webhooks/dashboard-ui",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Webhook Monitoring Dashboard" in response.text

    def test_get_dashboard_ui_unauthorized(self, db_client):
        """UI дашборд без авторизации."""
        response = db_client.get("/api/monitoring/webhooks/dashboard-ui")
        assert response.status_code == 401
