"""
Tests for API versioning.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash


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


class TestAPIVersioningViaPath:
    """Тесты версионирования через путь URL."""

    def test_api_v1_health(self, db_client):
        """Проверка health endpoint v1."""
        response = db_client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"

    def test_api_v2_info(self, db_client):
        """Проверка info endpoint v2."""
        response = db_client.get("/api/v2/")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.0.0"
        assert data["status"] == "development"

    def test_api_v1_auth_login(self, db_client, db_session):
        """Проверка login endpoint v1."""
        # Создаём пользователя
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        
        response = db_client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "TestPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
        assert response.headers["X-API-Version"] == "v1"


class TestAPIVersioningViaHeader:
    """Тесты версионирования через заголовок."""

    def test_x_api_version_header_v1(self, db_client):
        """Проверка X-API-Version заголовка v1."""
        response = db_client.get(
            "/health",
            headers={"X-API-Version": "v1"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_x_api_version_header_v2(self, db_client):
        """Проверка X-API-Version заголовка v2."""
        response = db_client.get(
            "/health",
            headers={"X-API-Version": "v2"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v2"

    def test_x_api_version_invalid(self, db_client):
        """Проверка невалидной версии."""
        response = db_client.get(
            "/health",
            headers={"X-API-Version": "v3"}
        )
        # v3 не поддерживается
        assert response.status_code in [200, 400]


class TestAPIVersioningViaAcceptHeader:
    """Тесты версионирования через Accept header."""

    def test_accept_header_version_v1(self, db_client):
        """Проверка version parameter в Accept."""
        response = db_client.get(
            "/health",
            headers={"Accept": "application/json; version=v1"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_accept_header_media_type_v1(self, db_client):
        """Проверка media type versioning."""
        response = db_client.get(
            "/health",
            headers={"Accept": "application/vnd.fastpay.v1+json"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"


class TestLegacyEndpoints:
    """Тесты legacy endpoints (без версии)."""

    def test_legacy_health(self, db_client):
        """Проверка legacy health endpoint."""
        response = db_client.get("/health")
        assert response.status_code == 200
        # Legacy endpoints не добавляют X-API-Version

    def test_legacy_auth_login(self, db_client, db_session):
        """Проверка legacy login endpoint."""
        user = User(
            username="legacyuser",
            email="legacy@example.com",
            hashed_password=get_password_hash("LegacyPass123!"),
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
        
        response = db_client.post(
            "/api/auth/login",
            data={"username": "legacyuser", "password": "LegacyPass123!"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestVersionPriority:
    """Тесты приоритета определения версии."""

    def test_path_priority_over_header(self, db_client):
        """Путь URL имеет приоритет над заголовком."""
        response = db_client.get(
            "/api/v1/health",
            headers={"X-API-Version": "v2"}
        )
        # Путь v1 имеет приоритет
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_header_priority_over_accept(self, db_client):
        """Заголовок имеет приоритет над Accept."""
        response = db_client.get(
            "/health",
            headers={
                "X-API-Version": "v1",
                "Accept": "application/json; version=v2"
            }
        )
        # Заголовок v1 имеет приоритет
        assert response.headers["X-API-Version"] == "v1"


class TestAdminEndpointsWithVersioning:
    """Тесты admin endpoints с версионированием."""

    def test_admin_statistics_v1(self, db_client, admin_token):
        """Проверка statistics endpoint v1."""
        response = db_client.get(
            "/api/v1/admin/payments/statistics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 200 или 404 (если нет платежей)
        assert response.status_code in [200, 404]
        assert response.headers["X-API-Version"] == "v1"

    def test_admin_dashboard_v1(self, db_client, admin_token):
        """Проверка dashboard endpoint v1."""
        response = db_client.get(
            "/api/v1/admin/payments/dashboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # 200 или 404 (если нет платежей)
        assert response.status_code in [200, 404]
        assert response.headers["X-API-Version"] == "v1"


class TestVersionedResponseHeaders:
    """Тесты заголовков в ответах."""

    def test_version_header_in_response(self, db_client):
        """Проверка наличия X-API-Version в ответе."""
        response = db_client.get("/api/v1/health")
        assert "X-API-Version" in response.headers
        
    def test_version_matches_request(self, db_client):
        """Проверка что версия в ответе совпадает с запрошенной."""
        response_v1 = db_client.get("/api/v1/health")
        assert response_v1.headers["X-API-Version"] == "v1"
        
        response_v2 = db_client.get("/api/v2/")
        assert response_v2.headers["X-API-Version"] == "v2"
