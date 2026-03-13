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
            hello
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["hello"] == "Hello from FastPay Connect GraphQL!"

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
            payments(page: 1, pageSize: 10, status: PENDING) {
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
        assert data["data"]["payments"]["page"] == 1
        assert data["data"]["payments"]["pageSize"] == 10


class TestGraphQLIntrospection:
    """Тесты GraphQL Introspection."""

    def test_schema_introspection(self, client):
        """Тест introspection query."""
        query = """
        query {
            __schema {
                queryType {
                    name
                    fields {
                        name
                    }
                }
                mutationType {
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
                    type {
                        name
                    }
                }
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__type" in data["data"]
        assert data["data"]["__type"]["name"] == "Payment"


class TestGraphQLErrors:
    """Тесты ошибок GraphQL."""

    def test_invalid_query(self, client):
        """Тест невалидной query."""
        query = """
        query {
            nonExistentField
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    def test_syntax_error(self, client):
        """Тест синтаксической ошибки."""
        query = """
        query {
            hello
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data

    def test_empty_query(self, client):
        """Тест пустой query."""
        response = client.post("/graphql", json={"query": ""})
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data


class TestGraphQLPaymentQueries:
    """Тесты query платежей."""

    def test_payment_by_order_id(self, client):
        """Тест получения платежа по order_id."""
        query = """
        query {
            payment(orderId: "order_001") {
                id
                orderId
                amount
                status
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        # payment может быть null если не существует
        assert "payment" in data["data"]

    def test_payments_with_sorting(self, client):
        """Тест сортировки платежей."""
        query = """
        query {
            payments(sortBy: "amount", sortOrder: "asc", pageSize: 5) {
                items {
                    id
                    amount
                }
                total
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "payments" in data["data"]

    def test_payments_with_search(self, client):
        """Тест поиска платежей."""
        query = """
        query {
            payments(search: "order", pageSize: 10) {
                items {
                    id
                    orderId
                }
                total
            }
        }
        """
        response = client.post("/graphql", json={"query": query})
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
