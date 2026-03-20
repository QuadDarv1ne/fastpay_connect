"""
Performance benchmarks and load testing for FastPay Connect.

Запуск:
    pytest tests/test_benchmarks.py -v --benchmark-only

Требования:
    pip install pytest-benchmark locust
"""

import pytest
import time
import random
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed


# =============================================================================
# Unit Benchmarks (pytest-benchmark)
# =============================================================================

@pytest.mark.benchmark(group="payment_creation")
def test_benchmark_payment_creation_simple(benchmark):
    """Бенчмарк создания простого платежа."""
    from app.schemas.payment import PaymentRequest
    
    def create_payment():
        return PaymentRequest(
            order_id=f"order_{random.randint(1, 100000)}",
            amount=1000.0,
            currency="RUB",
            description="Test payment",
            payment_gateway="yookassa"
        )
    
    result = benchmark(create_payment)
    assert result.amount == 1000.0


@pytest.mark.benchmark(group="signature_verification")
def test_benchmark_hmac_signature_verification(benchmark):
    """Бенчмарк проверки HMAC подписи."""
    import hmac
    import hashlib
    
    payload = b'{"order_id": "123", "amount": 1000}'
    secret = "test_secret_key"
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    
    def verify():
        computed = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)
    
    result = benchmark(verify)
    assert result is True


@pytest.mark.benchmark(group="repository_operations")
def test_benchmark_payment_repository_get_by_id(benchmark, db_session):
    """Бенчмарк получения платежа из БД."""
    from app.repositories.payment_repository import PaymentRepository
    from app.models.payment import Payment, PaymentStatus
    
    # Создаём тестовый платёж
    test_payment = Payment(
        order_id=f"bench_order_{random.randint(1, 100000)}",
        payment_gateway="yookassa",
        amount=1000.0,
        currency="RUB",
        status=PaymentStatus.PENDING,
        description="Benchmark test"
    )
    db_session.add(test_payment)
    db_session.commit()
    
    repo = PaymentRepository(db_session)
    
    def get_payment():
        return repo.get_by_order_id(test_payment.order_id)
    
    result = benchmark(get_payment)
    assert result is not None
    assert result.order_id == test_payment.order_id


@pytest.mark.benchmark(group="currency_conversion")
def test_benchmark_currency_conversion(benchmark):
    """Бенчмарк конвертации валюты."""
    from app.utils.currency import CurrencyService
    
    service = CurrencyService()
    
    def convert():
        return service.convert(1000.0, "RUB", "USD")
    
    result = benchmark(convert)
    assert result is not None


# =============================================================================
# Load Testing (Locust)
# =============================================================================

"""
Locust load test file.

Запуск:
    locust -f tests/test_benchmarks.py --host=http://localhost:8080
    
Web UI:
    http://localhost:8090
"""

try:
    from locust import HttpUser, task, between, events
    import json
    
    class PaymentApiUser(HttpUser):
        """Virtual user for load testing Payment API."""
        
        wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
        host = "http://localhost:8080"
        
        @task(3)
        def health_check(self):
            """Load test health endpoint."""
            self.client.get("/health")
        
        @task(2)
        def get_payment_analytics(self):
            """Load test analytics endpoint."""
            self.client.get(
                "/api/payments/analytics/summary",
                params={"days": 30}
            )
        
        @task(1)
        def create_payment(self):
            """Load test payment creation."""
            payload = {
                "order_id": f"load_test_{int(time.time())}",
                "amount": random.randint(100, 10000),
                "currency": "RUB",
                "description": "Load test payment",
                "payment_gateway": "yookassa"
            }
            self.client.post(
                "/api/v1/payments/create",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
    
    class WebhookApiUser(HttpUser):
        """Virtual user for load testing Webhook API."""
        
        wait_time = between(0.5, 2)
        
        @task(5)
        def webhook_health(self):
            """Test webhook monitoring endpoint."""
            self.client.get("/api/monitoring/webhooks/stats")
        
        @task(2)
        def get_webhook_events(self):
            """Test webhook events listing."""
            self.client.get(
                "/api/webhooks/events",
                params={"page": 1, "page_size": 20}
            )

except ImportError:
    # Locust not installed
    pass


# =============================================================================
# Concurrent Load Test
# =============================================================================

class ConcurrentLoadTester:
    """Тестирование под конкурентной нагрузкой."""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.results: Dict[str, Any] = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "response_times": [],
        }
    
    def make_request(self, endpoint: str, method: str = "GET") -> Dict[str, Any]:
        """Сделать HTTP запрос."""
        import httpx
        
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            with httpx.Client() as client:
                if method == "GET":
                    response = client.get(url, timeout=5.0)
                elif method == "POST":
                    response = client.post(url, json={}, timeout=5.0)
                
                elapsed = time.time() - start_time
                
                return {
                    "status_code": response.status_code,
                    "elapsed": elapsed,
                    "success": response.status_code == 200
                }
        except Exception as e:
            return {
                "error": str(e),
                "elapsed": time.time() - start_time,
                "success": False
            }
    
    def run_concurrent_test(
        self,
        endpoint: str,
        num_workers: int = 10,
        num_requests: int = 100
    ) -> Dict[str, Any]:
        """
        Запустить конкурентный тест.
        
        Args:
            endpoint: Endpoint для тестирования
            num_workers: Количество параллельных воркеров
            num_requests: Общее количество запросов
        
        Returns:
            Статистика теста
        """
        self.results = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "response_times": [],
            "min_response_time": float('inf'),
            "max_response_time": 0,
            "avg_response_time": 0,
            "requests_per_second": 0,
        }
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(self.make_request, endpoint)
                for _ in range(num_requests)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                self.results["total_requests"] += 1
                
                if result.get("success"):
                    self.results["successful"] += 1
                else:
                    self.results["failed"] += 1
                
                elapsed = result.get("elapsed", 0)
                self.results["response_times"].append(elapsed)
                self.results["min_response_time"] = min(
                    self.results["min_response_time"], elapsed
                )
                self.results["max_response_time"] = max(
                    self.results["max_response_time"], elapsed
                )
        
        total_time = time.time() - start_time
        
        if self.results["response_times"]:
            self.results["avg_response_time"] = (
                sum(self.results["response_times"]) / len(self.results["response_times"])
            )
        
        self.results["requests_per_second"] = (
            self.results["total_requests"] / total_time if total_time > 0 else 0
        )
        
        # Calculate percentiles
        sorted_times = sorted(self.results["response_times"])
        n = len(sorted_times)
        
        self.results["p50"] = sorted_times[int(n * 0.5)] if n > 0 else 0
        self.results["p90"] = sorted_times[int(n * 0.9)] if n > 0 else 0
        self.results["p95"] = sorted_times[int(n * 0.95)] if n > 0 else 0
        self.results["p99"] = sorted_times[int(n * 0.99)] if n > 0 else 0
        
        return self.results


# =============================================================================
# pytest fixtures
# =============================================================================

@pytest.fixture
def db_session():
    """Create a test database session."""
    from app.database import SessionLocal, engine, Base
    
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


# =============================================================================
# Run benchmarks
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("=" * 70)
    print("FastPay Connect - Performance Benchmarks")
    print("=" * 70)
    
    # Run concurrent load test
    tester = ConcurrentLoadTester()
    
    print("\nRunning concurrent load test on /health...")
    results = tester.run_concurrent_test(
        endpoint="/health",
        num_workers=10,
        num_requests=100
    )
    
    print(f"\nResults:")
    print(f"  Total Requests: {results['total_requests']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Requests/sec: {results['requests_per_second']:.2f}")
    print(f"  Min Response: {results['min_response_time']*1000:.2f}ms")
    print(f"  Max Response: {results['max_response_time']*1000:.2f}ms")
    print(f"  Avg Response: {results['avg_response_time']*1000:.2f}ms")
    print(f"  P50: {results['p50']*1000:.2f}ms")
    print(f"  P90: {results['p90']*1000:.2f}ms")
    print(f"  P95: {results['p95']*1000:.2f}ms")
    print(f"  P99: {results['p99']*1000:.2f}ms")
    
    sys.exit(0 if results['failed'] == 0 else 1)
