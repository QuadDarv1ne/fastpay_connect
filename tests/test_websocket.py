"""
Tests for WebSocket notifications.
"""

import pytest
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash, create_access_token
from datetime import timedelta


@pytest.fixture
def db_session(db_engine):
    """Create database session."""
    from sqlalchemy.orm import sessionmaker
    
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=db_engine
    )
    
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def test_user(db_session):
    """Create test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        is_superuser=False,
        roles='["viewer"]',
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create JWT token for test user."""
    token = create_access_token(
        data={"sub": test_user.username, "user_id": test_user.id, "roles": test_user.get_roles()},
        expires_delta=timedelta(minutes=30),
    )
    return token


class TestWebSocketConnection:
    """Тесты подключения WebSocket."""

    def test_websocket_connect_success(self, client, auth_token):
        """Успешное подключение WebSocket."""
        with client.websocket_connect("/ws/notifications", params={"token": auth_token}) as websocket:
            # Получаем приветственное сообщение
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "user_id" in data["data"]

    def test_websocket_connect_no_token(self, client):
        """Подключение без токена."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/notifications"):
                pass
        assert exc_info.value.code == 4001

    def test_websocket_connect_invalid_token(self, client):
        """Подключение с невалидным токеном."""
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/notifications", params={"token": "invalid_token"}):
                pass
        assert exc_info.value.code == 4002


class TestWebSocketSubscriptions:
    """Тесты подписок WebSocket."""

    def test_subscribe_to_order(self, client, auth_token):
        """Подписка на уведомления о заказе."""
        with client.websocket_connect(
            "/ws/notifications",
            params={"token": auth_token, "order_id": "order_123"}
        ) as websocket:
            # Приветственное сообщение
            data = websocket.receive_json()
            assert data["type"] == "connected"
            
            # Сообщение о подписке
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["data"]["order_id"] == "order_123"

    def test_subscribe_to_gateway(self, client, auth_token):
        """Подписка на уведомления о gateway."""
        with client.websocket_connect(
            "/ws/notifications",
            params={"token": auth_token, "gateway": "yookassa"}
        ) as websocket:
            # Приветственное сообщение
            data = websocket.receive_json()
            assert data["type"] == "connected"
            
            # Сообщение о подписке
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["data"]["gateway"] == "yookassa"

    def test_dynamic_subscribe_to_order(self, client, auth_token):
        """Динамическая подписка на заказ."""
        with client.websocket_connect("/ws/notifications", params={"token": auth_token}) as websocket:
            # Приветственное сообщение
            websocket.receive_json()
            
            # Подписка на заказ
            websocket.send_json({"action": "subscribe", "order_id": "order_456"})
            data = websocket.receive_json()
            
            assert data["type"] == "subscribed"
            assert data["data"]["order_id"] == "order_456"

    def test_dynamic_unsubscribe_from_order(self, client, auth_token):
        """Отписка от заказа."""
        with client.websocket_connect(
            "/ws/notifications",
            params={"token": auth_token, "order_id": "order_789"}
        ) as websocket:
            # Получаем приветствие и подписку
            websocket.receive_json()
            websocket.receive_json()
            
            # Отписка
            websocket.send_json({"action": "unsubscribe", "order_id": "order_789"})
            data = websocket.receive_json()
            
            assert data["type"] == "unsubscribed"
            assert data["data"]["order_id"] == "order_789"


class TestWebSocketStats:
    """Тесты статистики WebSocket."""

    def test_get_stats(self, client, auth_token):
        """Получение статистики подключений."""
        with client.websocket_connect("/ws/notifications", params={"token": auth_token}) as websocket:
            # Приветственное сообщение
            websocket.receive_json()
            
            # Запрос статистики
            websocket.send_json({"action": "get_stats"})
            data = websocket.receive_json()
            
            assert data["type"] == "stats"
            assert "total_connections" in data["data"]
            assert "unique_users" in data["data"]

    def test_websocket_stats_endpoint(self, client, auth_token):
        """Тест REST endpoint статистики."""
        response = client.get(
            "/ws/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data


class TestWebSocketMessages:
    """Тесты сообщений WebSocket."""

    def test_invalid_json_message(self, client, auth_token):
        """Отправка невалидного JSON."""
        with client.websocket_connect("/ws/notifications", params={"token": auth_token}) as websocket:
            # Приветственное сообщение
            websocket.receive_json()
            
            # Отправка невалидного JSON
            websocket.send_text("not valid json")
            data = websocket.receive_json()
            
            assert data["type"] == "error"
            assert "Invalid JSON" in data["data"]["message"]

    def test_unknown_action(self, client, auth_token):
        """Отправка неизвестной команды."""
        with client.websocket_connect("/ws/notifications", params={"token": auth_token}) as websocket:
            # Приветственное сообщение
            websocket.receive_json()
            
            # Отправка неизвестной команды
            websocket.send_json({"action": "unknown_action"})
            data = websocket.receive_json()
            
            assert data["type"] == "error"
            assert "Unknown action" in data["data"]["message"]


class TestWebSocketDisconnect:
    """Тесты отключения WebSocket."""

    def test_websocket_disconnect(self, client, auth_token):
        """Корректное отключение WebSocket."""
        websocket = client.websocket_connect("/ws/notifications", params={"token": auth_token})
        with websocket:
            # Приветственное сообщение
            websocket.receive_json()
        
        # После выхода из контекста подключение должно быть закрыто
