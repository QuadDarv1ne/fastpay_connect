"""
Tests for OAuth2 authentication.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.utils.security import get_password_hash, create_refresh_token
from datetime import timedelta


@pytest.fixture
def test_user(db: Session):
    """Создание тестового пользователя."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPass123!"),
        is_active=True,
        is_superuser=False,
        roles='["viewer"]',
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


@pytest.fixture
def test_admin_user(db: Session):
    """Создание тестового администратора."""
    user = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPass123!"),
        is_active=True,
        is_superuser=True,
        roles='["admin"]',
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    yield user
    db.delete(user)
    db.commit()


class TestRegister:
    """Тесты регистрации пользователя."""

    def test_register_success(self, client: TestClient):
        """Успешная регистрация."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "NewPass123!",
                "roles": ["viewer"],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"
        assert data["is_active"] is True
        assert "id" in data

    def test_register_duplicate_username(self, client: TestClient, test_user):
        """Регистрация с существующим username."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "NewPass123!",
            },
        )
        assert response.status_code == 400

    def test_register_duplicate_email(self, client: TestClient, test_user):
        """Регистрация с существующим email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "differentuser",
                "email": "test@example.com",
                "password": "NewPass123!",
            },
        )
        assert response.status_code == 400

    def test_register_short_password(self, client: TestClient):
        """Регистрация с коротким паролем."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "shortpass",
                "email": "short@example.com",
                "password": "short",
            },
        )
        # Pydantic валидация возвращает 422
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Регистрация с невалидным email."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "invalidemail",
                "email": "not-an-email",
                "password": "ValidPass123!",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Тесты аутентификации."""

    def test_login_success(self, client: TestClient, test_user):
        """Успешный вход."""
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_login_wrong_password(self, client: TestClient, test_user):
        """Вход с неправильным паролем."""
        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "WrongPass123!"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Вход с несуществующим пользователем."""
        response = client.post(
            "/api/auth/login",
            data={"username": "nouser", "password": "Pass123!"},
        )
        assert response.status_code == 401

    def test_login_json_success(self, client: TestClient, test_user):
        """Успешный вход через JSON."""
        response = client.post(
            "/api/auth/login/json",
            json={"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_disabled_user(self, client: TestClient, test_user, db: Session):
        """Вход для деактивированного пользователя."""
        test_user.is_active = False
        db.commit()

        response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 403


class TestRefreshToken:
    """Тесты обновления токена."""

    def test_refresh_token_success(self, client: TestClient, test_user):
        """Успешное обновление токена."""
        import time
        
        # Получаем токены
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        tokens = login_response.json()
        refresh_token = tokens["refresh_token"]
        
        # Небольшая задержка чтобы токены отличались по времени
        time.sleep(2)

        # Обновляем токен
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # Проверяем что refresh токены разные (новый был сгенерирован)
        assert data["refresh_token"] != refresh_token

    def test_refresh_token_invalid(self, client: TestClient):
        """Обновление с невалидным токеном."""
        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )
        assert response.status_code == 401

    def test_refresh_token_expired(self, client: TestClient, test_user):
        """Обновление с истёкшим токеном."""
        # Создаём просроченный refresh токен
        expired_token = create_refresh_token(
            data={"sub": "testuser", "user_id": test_user.id},
            expires_delta=timedelta(seconds=-1),
        )

        response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": expired_token},
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Тесты получения информации о текущем пользователе."""

    def test_get_current_user_info(self, client: TestClient, test_user):
        """Получение информации о себе."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        # Получение информации
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_get_current_user_no_token(self, client: TestClient):
        """Получение информации без токена."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client: TestClient):
        """Получение информации с невалидным токеном."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401


class TestChangePassword:
    """Тесты смены пароля."""

    def test_change_password_success(self, client: TestClient, test_user):
        """Успешная смена пароля."""
        # Login
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        # Смена пароля
        response = client.post(
            "/api/auth/change-password",
            json={
                "old_password": "TestPass123!",
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

        # Вход с новым паролем
        new_login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "NewPass456!"},
        )
        assert new_login_response.status_code == 200

    def test_change_password_wrong_old(self, client: TestClient, test_user):
        """Смена пароля с неправильным старым паролем."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/change-password",
            json={
                "old_password": "WrongPass!",
                "new_password": "NewPass456!",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


class TestLogout:
    """Тесты выхода из системы."""

    def test_logout_success(self, client: TestClient, test_user):
        """Успешный выход."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestAdminAccess:
    """Тесты доступа к admin endpoints."""

    def test_admin_endpoint_with_admin_user(self, client: TestClient, test_admin_user):
        """Доступ админа к admin endpoint."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testadmin", "password": "AdminPass123!"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/admin/payments/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Должен вернуть 200 или 404 (если нет платежей)
        assert response.status_code in [200, 404]

    def test_admin_endpoint_with_viewer(self, client: TestClient, test_user):
        """Доступ viewer к admin endpoint."""
        login_response = client.post(
            "/api/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/admin/payments/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_endpoint_no_auth(self, client: TestClient):
        """Доступ без аутентификации к admin endpoint."""
        response = client.get("/admin/payments/statistics")
        assert response.status_code == 401
