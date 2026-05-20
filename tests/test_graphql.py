"""
Tests for GraphQL API.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Test client."""
    with TestClient(app) as client:
        yield client


class TestGraphQLQuery:
    """Тесты GraphQL Query."""

    def test_hello_query(self, client):
        """Тест простой query."""
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
        assert "statistics" in data["data"]

    def test_statistics_query(self, client):
        """Тест query статистики."""
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
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "statistics" in data["data"]
        assert "totalPayments" in data["data"]["statistics"]
        assert "totalAmount" in data["data"]["statistics"]

    def test_payments_query_default_pagination(self, client):
        """Тест query платежей с пагинацией по умолчанию."""
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
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "payments" in data["data"]
        assert "items" in data["data"]["payments"]
        assert "total" in data["data"]["payments"]
        assert data["data"]["payments"]["page"] == 1
        assert data["data"]["payments"]["pageSize"] == 20

    def test_payments_query_with_filters(self, client):
        """Тест query платежей с фильтрами."""
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
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "payments" in data["data"]
        assert "total" in data["data"]["payments"]


class TestGraphQLIntrospection:
    """Тесты GraphQL introspection."""

    def test_schema_introspection(self, client):
        """Тест schema introspection."""
        query = """
        query {
            __schema {
                queryType {
                    name
                }
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]
        assert "queryType" in data["data"]["__schema"]

    def test_type_introspection(self, client):
        """Тест introspection типа."""
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
        response = client.post("/graphql", json={"query": query})
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
