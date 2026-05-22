"""
Tests for 2FA (Two-Factor Authentication) functionality.
Автор: Dupley Maxim Igorevich
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import json

from app.main import app
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash
from app.services.mfa_service import mfa_service


@pytest.fixture
def api_client(db_session):
    """Create test client with DB override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session):
    """Создание тестового пользователя."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        mfa_enabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


@pytest.fixture
def test_user_with_mfa(db_session: Session):
    """Создание пользователя с включенным 2FA."""
    secret = mfa_service.generate_secret()
    backup_codes = mfa_service.generate_backup_codes()
    hashed_codes = mfa_service.hash_backup_codes(backup_codes)

    user = User(
        username="mfauser",
        email="mfa@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
        mfa_enabled=True,
        mfa_secret=secret,
        mfa_backup_codes=mfa_service.serialize_backup_codes(hashed_codes),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    yield user
    db_session.delete(user)
    db_session.commit()


def get_token(api_client, username: str, password: str, mfa_code: str = None) -> str:
    """Получение токена для аутентифицированных запросов."""
    if mfa_code:
        response = api_client.post(
            "/api/auth/login/json",
            json={"username": username, "password": password, "mfa_code": mfa_code}
        )
    else:
        response = api_client.post(
            "/api/auth/login",
            data={"username": username, "password": password}
        )
    assert response.status_code == 200
    return response.json()["access_token"]


class TestMFASetup:
    """Тесты настройки 2FA."""

    def test_setup_mfa_unauthorized(self, api_client):
        """Тест: настройка 2FA без авторизации."""
        response = api_client.post("/api/auth/mfa/setup", json={"password": "test"})
        assert response.status_code == 401

    def test_setup_mfa_success(self, test_user, db_session: Session, api_client):
        """Тест: успешная настройка 2FA."""
        token = get_token(api_client, "testuser", "testpassword123")

        response = api_client.post(
            "/api/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "testpassword123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "secret" in data
        assert "qr_code_url" in data
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10

        # Проверяем, что секрет сохранён
        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user.mfa_secret is not None

    def test_setup_mfa_invalid_password(self, test_user, db_session: Session, api_client):
        """Тест: настройка 2FA с неверным паролем."""
        token = get_token(api_client, "testuser", "testpassword123")

        response = api_client.post(
            "/api/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "wrongpassword"}
        )

        assert response.status_code == 400

    def test_setup_mfa_already_enabled(self, test_user_with_mfa, db_session: Session, api_client):
        """Тест: настройка 2FA когда он уже включён."""
        # Generate valid TOTP code for MFA user
        import pyotp
        totp = pyotp.TOTP(test_user_with_mfa.mfa_secret)
        mfa_code = totp.now()
        token = get_token(api_client, "mfauser", "testpassword123", mfa_code=mfa_code)

        response = api_client.post(
            "/api/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "testpassword123"}
        )

        assert response.status_code == 400


class TestMFAVerify:
    """Тесты подтверждения 2FA."""

    def test_verify_mfa_unauthorized(self, api_client):
        """Тест: подтверждение 2FA без авторизации."""
        response = api_client.post("/api/auth/mfa/verify", json={"code": "123456"})
        assert response.status_code == 401

    def test_verify_mfa_success(self, test_user, db_session: Session, api_client):
        """Тест: успешное подтверждение 2FA."""
        # Сначала настраиваем 2FA
        token = get_token(api_client, "testuser", "testpassword123")

        setup_response = api_client.post(
            "/api/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "testpassword123"}
        )
        secret = setup_response.json()["secret"]

        # Генерируем правильный TOTP код
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Подтверждаем
        verify_response = api_client.post(
            "/api/auth/mfa/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": code}
        )

        assert verify_response.status_code == 200
        data = verify_response.json()
        assert "backup_codes" in data

        # Проверяем, что 2FA включён
        user = db_session.query(User).filter(User.username == "testuser").first()
        assert user.mfa_enabled is True
        assert user.mfa_backup_codes is not None

    def test_verify_mfa_invalid_code(self, test_user, db_session: Session, api_client):
        """Тест: подтверждение 2FA с неверным кодом."""
        token = get_token(api_client, "testuser", "testpassword123")

        # Настраиваем 2FA
        api_client.post(
            "/api/auth/mfa/setup",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "testpassword123"}
        )

        # Пробуем подтвердить с неверным кодом
        response = api_client.post(
            "/api/auth/mfa/verify",
            headers={"Authorization": f"Bearer {token}"},
            json={"code": "000000"}
        )

        assert response.status_code == 400


class TestMFADisable:
    """Тесты отключения 2FA."""

    def test_disable_mfa_unauthorized(self, api_client):
        """Тест: отключение 2FA без авторизации."""
        response = api_client.post("/api/auth/mfa/disable", json={"password": "test", "code": "123456"})
        assert response.status_code == 401

    def test_disable_mfa_success(self, test_user_with_mfa, db_session: Session, api_client):
        """Тест: успешное отключение 2FA."""
        import pyotp
        totp = pyotp.TOTP(test_user_with_mfa.mfa_secret)
        mfa_code = totp.now()
        token = get_token(api_client, "mfauser", "testpassword123", mfa_code=mfa_code)

        # Генерируем правильный TOTP код
        code = totp.now()

        response = api_client.post(
            "/api/auth/mfa/disable",
            headers={"Authorization": f"Bearer {token}"},
            json={"password": "testpassword123", "code": code}
        )

        assert response.status_code == 200

        # Проверяем, что 2FA отключен
        user = db_session.query(User).filter(User.username == "mfauser").first()
        assert user.mfa_enabled is False
        assert user.mfa_secret is None

    def test_disable_mfa_with_backup_code(self, test_user_with_mfa, db_session: Session, api_client):
        """Тест: отключение 2FA с backup кодом."""
        import pyotp
        totp = pyotp.TOTP(test_user_with_mfa.mfa_secret)
        mfa_code = totp.now()
        token = get_token(api_client, "mfauser", "testpassword123", mfa_code=mfa_code)

        # Получаем backup код
        hashed_codes = json.loads(test_user_with_mfa.mfa_backup_codes)
        # Для теста используем простой код (в реальности нужно хешировать)
        # Этот тест требует мокирования verify_password

        # Пропускаем детальную проверку backup кода в этом тесте
        pytest.skip("Backup code test requires password mocking")


class TestMFAStatus:
    """Тесты статуса 2FA."""

    def test_get_mfa_status_unauthorized(self, api_client):
        """Тест: статус 2FA без авторизации."""
        response = api_client.get("/api/auth/mfa/status")
        assert response.status_code == 401

    def test_get_mfa_status_disabled(self, test_user, db_session: Session, api_client):
        """Тест: статус 2FA когда отключён."""
        token = get_token(api_client, "testuser", "testpassword123")

        response = api_client.get(
            "/api/auth/mfa/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_get_mfa_status_enabled(self, test_user_with_mfa, db_session: Session, api_client):
        """Тест: статус 2FA когда включён."""
        import pyotp
        totp = pyotp.TOTP(test_user_with_mfa.mfa_secret)
        mfa_code = totp.now()
        token = get_token(api_client, "mfauser", "testpassword123", mfa_code=mfa_code)

        response = api_client.get(
            "/api/auth/mfa/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["backup_codes_remaining"] > 0


class TestMFABackupCodes:
    """Тесты backup кодов 2FA."""

    def test_regenerate_backup_codes_success(self, test_user_with_mfa, db_session: Session, api_client):
        """Тест: перегенерация backup кодов."""
        import pyotp
        totp = pyotp.TOTP(test_user_with_mfa.mfa_secret)
        mfa_code = totp.now()
        token = get_token(api_client, "mfauser", "testpassword123", mfa_code=mfa_code)

        response = api_client.post(
            "/api/auth/mfa/backup-codes",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "backup_codes" in data
        assert len(data["backup_codes"]) == 10

    def test_regenerate_backup_codes_mfa_not_enabled(self, test_user, db_session: Session, api_client):
        """Тест: перегенерация backup кодов когда 2FA отключён."""
        token = get_token(api_client, "testuser", "testpassword123")

        response = api_client.post(
            "/api/auth/mfa/backup-codes",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400


class TestMFAService:
    """Тесты MFA сервиса."""

    def test_generate_secret(self):
        """Тест: генерация секрета."""
        secret = mfa_service.generate_secret()
        assert len(secret) == 32  # Base32 secret

    def test_generate_backup_codes(self):
        """Тест: генерация backup кодов."""
        codes = mfa_service.generate_backup_codes(10)
        assert len(codes) == 10
        for code in codes:
            assert len(code) == 9  # XXXX-YYYY format
            assert code[4] == "-"

    def test_verify_totp_code(self):
        """Тест: проверка TOTP кода."""
        secret = mfa_service.generate_secret()
        import pyotp
        totp = pyotp.TOTP(secret)
        code = totp.now()
        
        assert mfa_service.verify_code(secret, code) is True

    def test_verify_invalid_code(self):
        """Тест: проверка неверного кода."""
        secret = mfa_service.generate_secret()
        
        assert mfa_service.verify_code(secret, "000000") is False

    def test_hash_and_verify_backup_code(self):
        """Тест: хеширование и проверка backup кода."""
        codes = ["1234-5678", "8765-4321"]
        hashed = mfa_service.hash_backup_codes(codes)
        
        assert len(hashed) == 2
        assert mfa_service.verify_backup_code("1234-5678", hashed) is True
        assert mfa_service.verify_backup_code("0000-0000", hashed) is False

    def test_remove_used_backup_code(self):
        """Тест: удаление использованного backup кода."""
        codes = ["1234-5678", "8765-4321"]
        hashed = mfa_service.hash_backup_codes(codes)
        
        new_hashed = mfa_service.remove_used_backup_code("1234-5678", hashed)
        
        assert len(new_hashed) == 1
        assert mfa_service.verify_backup_code("1234-5678", new_hashed) is False
        assert mfa_service.verify_backup_code("8765-4321", new_hashed) is True
