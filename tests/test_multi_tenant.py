"""
Tests for multi-tenant support.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Generator
import json

from app.database import Base
from app.models.tenant import Tenant, TenantStatus
from app.models.user import User
from app.models.payment import Payment, PaymentStatus
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.repositories.payment_repository import PaymentRepository
from app.utils.tenant import set_current_tenant, reset_tenant_context, get_current_tenant


@pytest.fixture(scope="function")
def test_db() -> Generator:
    """Фикстура для создания тестовой БД."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def tenant1(test_db) -> Tenant:
    """Фикстура для создания tenant1."""
    tenant = Tenant(
        name="Test Tenant 1",
        slug="test-tenant-1",
        api_key="test_api_key_1",
        status=TenantStatus.ACTIVE.value,
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant


@pytest.fixture
def tenant2(test_db) -> Tenant:
    """Фикстура для создания tenant2."""
    tenant = Tenant(
        name="Test Tenant 2",
        slug="test-tenant-2",
        api_key="test_api_key_2",
        status=TenantStatus.ACTIVE.value,
    )
    test_db.add(tenant)
    test_db.commit()
    test_db.refresh(tenant)
    return tenant


class TestTenantModel:
    """Тесты модели Tenant."""

    def test_tenant_creation(self, test_db):
        """Проверка создания tenant."""
        tenant = Tenant(
            name="Test Tenant",
            slug="test-tenant",
            api_key="test_api_key",
        )
        test_db.add(tenant)
        test_db.commit()

        assert tenant.id is not None
        assert tenant.name == "Test Tenant"
        assert tenant.slug == "test-tenant"
        assert tenant.status == TenantStatus.ACTIVE.value

    def test_tenant_get_settings(self, tenant1):
        """Проверка получения настроек tenant."""
        assert tenant1.get_settings() == {}

        tenant1.settings_json = json.dumps({"key": "value", "limit": 100})
        settings = tenant1.get_settings()
        assert settings == {"key": "value", "limit": 100}

    def test_tenant_get_allowed_gateways(self, tenant1):
        """Проверка получения разрешённых шлюзов."""
        assert tenant1.get_allowed_gateways() == []

        tenant1.allowed_payment_gateways = json.dumps(["yookassa", "tinkoff"])
        gateways = tenant1.get_allowed_gateways()
        assert gateways == ["yookassa", "tinkoff"]

    def test_tenant_is_gateway_allowed(self, tenant1):
        """Проверка проверки разрешённого шлюза."""
        tenant1.allowed_payment_gateways = json.dumps(["yookassa", "tinkoff"])

        assert tenant1.is_gateway_allowed("yookassa") is True
        assert tenant1.is_gateway_allowed("robokassa") is False

        # Если шлюзы не указаны, все разрешены
        tenant1.allowed_payment_gateways = None
        assert tenant1.is_gateway_allowed("any_gateway") is True


class TestTenantRepository:
    """Тесты TenantRepository."""

    def test_create_tenant(self, test_db):
        """Проверка создания tenant через репозиторий."""
        repo = TenantRepository(test_db)
        tenant = repo.create(
            name="New Tenant",
            slug="new-tenant",
            description="Test description",
            contact_email="test@example.com",
        )

        assert tenant is not None
        assert tenant.name == "New Tenant"
        assert tenant.api_key is not None
        assert len(tenant.api_key) > 30

    def test_create_tenant_duplicate_slug(self, test_db, tenant1):
        """Проверка создания tenant с дубликатом slug."""
        repo = TenantRepository(test_db)
        result = repo.create(
            name="Duplicate Tenant",
            slug=tenant1.slug,
        )
        assert result is None

    def test_get_by_slug(self, test_db, tenant1):
        """Проверка получения tenant по slug."""
        repo = TenantRepository(test_db)
        tenant = repo.get_by_slug(tenant1.slug)

        assert tenant is not None
        assert tenant.id == tenant1.id

    def test_get_by_api_key(self, test_db, tenant1):
        """Проверка получения tenant по API ключу."""
        repo = TenantRepository(test_db)
        tenant = repo.get_by_api_key(tenant1.api_key)

        assert tenant is not None
        assert tenant.id == tenant1.id

    def test_update_tenant(self, test_db, tenant1):
        """Проверка обновления tenant."""
        repo = TenantRepository(test_db)
        updated = repo.update(
            tenant=tenant1,
            name="Updated Name",
            description="Updated description",
        )

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    def test_regenerate_api_key(self, test_db, tenant1):
        """Проверка перегенерации API ключа."""
        repo = TenantRepository(test_db)
        old_key = tenant1.api_key

        new_key = repo.regenerate_api_key(tenant1)

        assert new_key is not None
        assert new_key != old_key
        assert len(new_key) > 30


class TestTenantContext:
    """Тесты tenant context."""

    def test_set_get_tenant(self, tenant1):
        """Проверка установки и получения tenant."""
        set_current_tenant(tenant1)
        current = get_current_tenant()

        assert current is not None
        assert current.id == tenant1.id
        assert current.slug == tenant1.slug

    def test_reset_tenant_context(self):
        """Проверка сброса контекста."""
        set_current_tenant(Tenant(id=1, name="Test", slug="test", api_key="key"))
        reset_tenant_context()

        assert get_current_tenant() is None


class TestTenantIsolation:
    """Тесты изоляции tenant'ов."""

    def test_payment_tenant_filter(self, test_db, tenant1, tenant2):
        """Проверка фильтрации платежей по tenant."""
        # Создаём платежи для разных tenant'ов
        payment1 = Payment(
            order_id="order-1",
            payment_gateway="yookassa",
            amount=100.0,
            tenant_id=tenant1.id,
        )
        payment2 = Payment(
            order_id="order-2",
            payment_gateway="yookassa",
            amount=200.0,
            tenant_id=tenant2.id,
        )
        test_db.add(payment1)
        test_db.add(payment2)
        test_db.commit()

        repo = PaymentRepository(test_db)

        # Устанавливаем tenant1 контекст
        set_current_tenant(tenant1)

        # Получаем платежи только для tenant1
        payments, total = repo.get_all_paginated()

        assert total == 1
        assert payments[0].order_id == "order-1"

        reset_tenant_context()

    def test_user_tenant_filter(self, test_db, tenant1, tenant2):
        """Проверка фильтрации пользователей по tenant."""
        from app.utils.security import get_password_hash

        user1 = User(
            username="user1",
            email="user1@test.com",
            hashed_password=get_password_hash("password"),
            tenant_id=tenant1.id,
        )
        user2 = User(
            username="user2",
            email="user2@test.com",
            hashed_password=get_password_hash("password"),
            tenant_id=tenant2.id,
        )
        test_db.add(user1)
        test_db.add(user2)
        test_db.commit()

        repo = UserRepository(test_db)

        # Устанавливаем tenant1 контекст
        set_current_tenant(tenant1)

        # Получаем пользователя только из tenant1
        user = repo.get_by_username("user1")

        assert user is not None
        assert user.username == "user1"
        assert user.tenant_id == tenant1.id

        reset_tenant_context()

    def test_statistics_tenant_isolation(self, test_db, tenant1, tenant2):
        """Проверка изоляции статистики."""
        # Создаём платежи для tenant1
        for i in range(3):
            payment = Payment(
                order_id=f"order-t1-{i}",
                payment_gateway="yookassa",
                amount=100.0,
                status=PaymentStatus.COMPLETED,
                tenant_id=tenant1.id,
            )
            test_db.add(payment)

        # Создаём платежи для tenant2
        for i in range(5):
            payment = Payment(
                order_id=f"order-t2-{i}",
                payment_gateway="yookassa",
                amount=200.0,
                status=PaymentStatus.COMPLETED,
                tenant_id=tenant2.id,
            )
            test_db.add(payment)

        test_db.commit()

        repo = PaymentRepository(test_db)

        # Статистика для tenant1
        set_current_tenant(tenant1)
        stats1 = repo.get_statistics()

        assert stats1["total_payments"] == 3
        assert stats1["total_completed_amount"] == 300.0

        # Статистика для tenant2
        set_current_tenant(tenant2)
        stats2 = repo.get_statistics()

        assert stats2["total_payments"] == 5
        assert stats2["total_completed_amount"] == 1000.0

        reset_tenant_context()


class TestTenantWithoutContext:
    """Тесты работы без tenant контекста."""

    def test_payment_without_tenant(self, test_db):
        """Проверка создания платежа без tenant."""
        repo = PaymentRepository(test_db)

        payment = repo.create(
            order_id="order-no-tenant",
            payment_gateway="yookassa",
            amount=100.0,
            description="Payment without tenant",
        )

        assert payment.tenant_id is None

    def test_get_all_without_tenant_filter(self, test_db, tenant1):
        """Проверка получения всех записей без tenant фильтра."""
        # Создаём платежи с tenant и без
        payment1 = Payment(
            order_id="order-with-tenant",
            payment_gateway="yookassa",
            amount=100.0,
            tenant_id=tenant1.id,
        )
        payment2 = Payment(
            order_id="order-without-tenant",
            payment_gateway="yookassa",
            amount=50.0,
            tenant_id=None,
        )
        test_db.add(payment1)
        test_db.add(payment2)
        test_db.commit()

        repo = PaymentRepository(test_db)

        # Без установленного контекста получаем все платежи
        payments, total = repo.get_all_paginated()

        assert total == 2
