# Performance Benchmarks & Load Testing

> Тестирование производительности FastPay Connect

---

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт)
- [pytest-benchmark](#-pytest-benchmark)
- [Locust Load Testing](#-locust-load-testing)
- [Concurrent Load Tester](#-concurrent-load-tester)
- [Метрики производительности](#-метрики-производительности)
- [Оптимизация](#-оптимизация)

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements-dev.txt
```

### 2. Запуск benchmarks

```bash
# Запустить все benchmarks
pytest tests/test_benchmarks.py -v --benchmark-only

# Запустить конкретный benchmark
pytest tests/test_benchmarks.py::test_benchmark_hmac_signature_verification -v

# Запустить с profiling
pytest tests/test_benchmarks.py -v --benchmark-cprofile
```

### 3. Запуск Locust

```bash
# Запуск Locust web UI
locust -f tests/test_benchmarks.py --host=http://localhost:8080

# Открыть в браузере
# http://localhost:8090
```

---

## 📊 pytest-benchmark

### Benchmark группы

**payment_creation:**
- Создание объекта PaymentRequest
- Валидация данных

**signature_verification:**
- HMAC-SHA256 подпись
- Constant-time comparison

**repository_operations:**
- Получение платежа из БД
- Поиск по order_id

**currency_conversion:**
- Конвертация валют
- Работа с курсами

### Пример запуска

```bash
$ pytest tests/test_benchmarks.py --benchmark-only

---------------------------------------------------------------------------------------------- benchmark: 4 tests ----------------------------------------------------------------------------------------------
Name (time in us)                              Min               Max              Mean            StdDev            Median               IQR            Outliers  OPS (Kops/s)            Rounds  Iterations
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_benchmark_hmac_signature_verification   1.5420 (1.0)      45.2310 (1.0)      1.6895 (1.0)      1.0234 (1.0)      1.6520 (1.0)      0.0620 (1.0)     184;254      591.8845 (1.0)       18938           1
test_benchmark_payment_creation_simple       5.2340 (3.39)     67.8920 (1.50)     5.6789 (3.36)     2.3456 (2.29)     5.4560 (3.30)     0.2340 (3.77)     89;156      176.0923 (0.30)       5000           1
test_benchmark_currency_conversion          12.3450 (8.01)     89.2340 (1.97)    13.4567 (7.96)     3.4567 (3.38)    12.8900 (7.80)     0.5670 (9.15)     67;89       74.3123 (0.13)       2000           1
test_benchmark_payment_repository_get_by_id 45.6780 (29.62)   234.5670 (5.19)    52.3456 (30.98)   12.3456 (12.06)   48.9012 (29.60)    2.3456 (37.83)    23;45       19.1023 (0.03)        500           1
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

### Интерпретация результатов

| Метрика | Описание | Хорошо |
|---------|----------|--------|
| **Min** | Минимальное время | < 10ms |
| **Max** | Максимальное время | < 100ms |
| **Mean** | Среднее время | < 20ms |
| **Median** | Медиана | < 15ms |
| **IQR** | Интерквартильный размах | < 5ms |
| **OPS** | Операций в секунду | > 1000 |
| **Outliers** | Выбросы | < 5% |

---

## 🐜 Locust Load Testing

### Web UI

1. Запустите Locust:
```bash
locust -f tests/test_benchmarks.py --host=http://localhost:8080
```

2. Откройте http://localhost:8090

3. Настройте тест:
   - **Number of users**: 100
   - **Ramp up users**: 10 users/sec
   - **Run time**: 5m

4. Нажмите "Start swarming"

### Консольный режим

```bash
# Запуск без UI
locust -f tests/test_benchmarks.py --host=http://localhost:8080 --headless -u 100 -r 10 -t 5m

# Экспорт результатов в JSON
locust -f tests/test_benchmarks.py --host=http://localhost:8080 --headless -u 100 -r 10 -t 5m --json > results.json
```

### Пользовательские сценарии

**PaymentApiUser:**
- Health check (weight: 3)
- Payment analytics (weight: 2)
- Create payment (weight: 1)

**WebhookApiUser:**
- Webhook health (weight: 5)
- Get webhook events (weight: 2)

### Пример отчёта Locust

```
Type     Name                                   # reqs      # fails |    Avg     Min     Max    Med |   req/s  failures/s
--------|---------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------
GET      /health                                   5000     0 (0%) |     12       2      89     10 |   833.33        0.00
GET      /api/payments/analytics/summary           3000     5 (0.17%) |     45       5     234     38 |   500.00        0.83
POST     /api/v1/payments/create                   1500    12 (0.80%) |    156      23     567    134 |   250.00        2.00
--------|---------------------------------------|-------|-------------|-------|-------|-------|-------|--------|-----------
         Total                                    9500    17 (0.18%) |     56       2     567     45 |  1583.33        2.83
```

---

## 🔁 Concurrent Load Tester

### Использование

```python
from tests.test_benchmarks import ConcurrentLoadTester

tester = ConcurrentLoadTester(base_url="http://localhost:8080")

results = tester.run_concurrent_test(
    endpoint="/health",
    num_workers=10,
    num_requests=100
)

print(f"Requests/sec: {results['requests_per_second']:.2f}")
print(f"P99 latency: {results['p99']*1000:.2f}ms")
```

### Метрики

| Метрика | Описание |
|---------|----------|
| **total_requests** | Всего запросов |
| **successful** | Успешных (200 OK) |
| **failed** | Ошибок |
| **requests_per_second** | Пропускная способность |
| **min_response_time** | Мин. время ответа |
| **max_response_time** | Макс. время ответа |
| **avg_response_time** | Среднее время |
| **p50/p90/p95/p99** | Перцентили |

---

## 📈 Метрики производительности

### Целевые показатели

| Endpoint | P95 | P99 | Error Rate |
|----------|-----|-----|------------|
| /health | < 50ms | < 100ms | < 0.1% |
| /api/v1/payments/* | < 500ms | < 1000ms | < 1% |
| /api/payments/analytics/* | < 1000ms | < 2000ms | < 1% |
| /webhooks/* | < 200ms | < 500ms | < 0.5% |

### Профилирование

```bash
# cProfile
python -m cProfile -o profile.stats run.py

# Визуализация
snakeviz profile.stats
```

### Memory profiling

```bash
# Установить
pip install memory-profiler

# Запустить
python -m memory_profiler run.py
```

---

## ⚡ Оптимизация

### Database

1. **Индексы**: Проверьте индексы на часто используемых полях
2. **Connection pool**: Настройте pool_size и max_overflow
3. **Async queries**: Используйте асинхронные запросы

```python
# alembic migration
CREATE INDEX ix_payments_status ON payments(status);
CREATE INDEX ix_payments_created ON payments(created_at);
```

### Caching

1. **Redis cache**: Кэшируйте частые запросы
2. **Rate limiting**: Используйте Redis для rate limiting
3. **Query cache**: Кэшируйте результаты сложных запросов

### Application

1. **Workers**: Увеличьте количество workers uvicorn
2. **Gzip**: Включите сжатие ответов
3. **Connection pooling**: Используйте pooling для внешних API

```bash
# Запуск с workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8080
```

---

## 📊 CI/CD Integration

### GitHub Actions

```yaml
name: Performance Tests

on:
  push:
    branches: [main, dev]

jobs:
  benchmarks:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
    
    - name: Run benchmarks
      run: |
        pytest tests/test_benchmarks.py --benchmark-only --benchmark-json=benchmark.json
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmark.json
```

### Performance gates

```yaml
# .github/workflows/performance-gates.yml
name: Performance Gates

on:
  pull_request:

jobs:
  performance-gates:
    runs-on: ubuntu-latest
    
    steps:
    - name: Check P95 latency
      run: |
        P95=$(jq '.benchmarks[].stats.p95' benchmark.json)
        if (( $(echo "$P95 > 0.1" | bc -l) )); then
          echo "P95 latency too high: ${P95}s"
          exit 1
        fi
```

---

## 🛠️ Troubleshooting

### Высокая задержка

1. Проверьте логи на медленные запросы
2. Проверьте нагрузку на БД
3. Проверьте network latency

### Много ошибок

1. Проверьте лимиты rate limiting
2. Проверьте доступность зависимостей
3. Проверьте логи ошибок

### Низкая пропускная способность

1. Увеличьте количество workers
2. Оптимизируйте медленные endpoint'ы
3. Используйте кэширование

---

## 📚 Дополнительные ресурсы

- [pytest-benchmark Documentation](https://pytest-benchmark.readthedocs.io/)
- [Locust Documentation](https://docs.locust.io/)
- [OpenTelemetry Performance](https://opentelemetry.io/docs/)

---

*Последнее обновление: Mar 2026*
