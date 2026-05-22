"""
Tests for GraphQL API.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.utils.security import get_password_hash


@pytest.fixture
def client():
    """Test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_client(db_session):
    """Test client with authentication."""
    from app.graphql.context import set_db_session_factory

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    set_db_session_factory(override_get_db)

    # Create test user
    user = User(
        username="graphql_test_user",
        email="graphql_test@example.com",
        hashed_password=get_password_hash("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Get auth token
    response = TestClient(app).post(
        "/api/auth/login",
        data={"username": "graphql_test_user", "password": "testpassword123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    with TestClient(app) as test_client:
        yield test_client, {"Authorization": f"Bearer {token}"}

    db_session.delete(user)
    db_session.commit()
    set_db_session_factory(None)
    app.dependency_overrides.clear()


class TestGraphQLQuery:
    """Тесты GraphQL Query."""

    def test_hello_query(self, auth_client):
        """Тест простой query."""
        client, headers = auth_client
        query = """
        query {
            statistics {
                totalPayments
                totalAmount
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "statistics" in data["data"]

    def test_statistics_query(self, auth_client):
        """Тест query статистики."""
        client, headers = auth_client
        query = """
        query {
            statistics {
                totalPayments
                totalAmount
                byStatus
                byGateway
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "statistics" in data["data"]
        assert "totalPayments" in data["data"]["statistics"]
        assert "totalAmount" in data["data"]["statistics"]

    def test_payments_query_default_pagination(self, auth_client):
        """Тест query платежей с пагинацией по умолчанию."""
        client, headers = auth_client
        query = """
        query {
            payments {
                items {
                    id
                    orderId
                    amount
                    status
                }
                total
                page
                pageSize
                pages
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "payments" in data["data"]
        assert "items" in data["data"]["payments"]
        assert "total" in data["data"]["payments"]
        assert data["data"]["payments"]["page"] == 1
        assert data["data"]["payments"]["pageSize"] == 20

    def test_payments_query_with_filters(self, auth_client):
        """Тест query платежей с фильтрами."""
        client, headers = auth_client
        query = """
        query {
            payments(page: 1, pageSize: 10) {
                items {
                    id
                    orderId
                    status
                }
                total
                page
                pageSize
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "payments" in data["data"]
        assert "total" in data["data"]["payments"]


class TestGraphQLIntrospection:
    """Тесты GraphQL introspection."""

    def test_schema_introspection(self, auth_client):
        """Тест schema introspection."""
        client, headers = auth_client
        query = """
        query {
            __schema {
                queryType {
                    name
                }
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]
        assert "queryType" in data["data"]["__schema"]

    def test_type_introspection(self, auth_client):
        """Тест introspection типа."""
        client, headers = auth_client
        query = """
        query {
            __type(name: "Payment") {
                name
                fields {
                    name
                }
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__type" in data["data"]


class TestGraphQLErrors:
    """Тесты ошибок GraphQL."""

    def test_invalid_query(self, client):
        """Тест invalid query."""
        response = client.post("/graphql", json={"query": "invalid {"})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    def test_empty_query(self, client):
        """Тест пустой query."""
        response = client.post("/graphql", json={"query": ""})
        assert response.status_code in (200, 400)
        if response.status_code == 200:
            data = response.json()
            assert "errors" in data

    def test_unknown_field(self, client):
        """Тест unknown field."""
        query = """
        query {
            unknownField
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data


class TestGraphQLAuth:
    """Тесты аутентификации GraphQL."""

    def test_unauthenticated_query_returns_empty(self, client):
        """Тест: неаутентифицированный запрос возвращает пустые результаты."""
        query = """
        query {
            payments {
                items {
                    id
                }
                total
                page
                pageSize
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Unauthenticated users get empty results
        assert data["data"]["payments"]["pageSize"] == 0

    def test_unauthenticated_statistics_returns_empty(self, client):
        """Тест: неаутентифицированный запрос статистики возвращает нули."""
        query = """
        query {
            statistics {
                totalPayments
                totalAmount
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Unauthenticated users get zero statistics
        assert data["data"]["statistics"]["totalPayments"] == 0
        assert data["data"]["statistics"]["totalAmount"] == 0

    def test_tenants_query_requires_admin(self, auth_client):
        """Тест: запрос тенантов требует прав администратора."""
        client, headers = auth_client
        query = """
        query {
            tenants {
                items {
                    id
                    name
                }
                total
            }
        }
        """
        response = client.post("/graphql", json={"query": query}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # Non-admin users get empty results for tenant queries
        assert data["data"]["tenants"]["total"] == 0
