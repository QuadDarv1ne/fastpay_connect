# Flower Dashboard Deployment Guide

> **Flower** — веб-интерфейс для мониторинга и управления задачами Celery.

---

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт)
- [Настройка аутентификации](#-настройка-аутентификации)
- [Доступ к Flower](#-доступ-к-flower)
- [API для управления](#-api-для-управления)
- [Production конфигурация](#-production-конфигурация)

---

## 🚀 Быстрый старт

### 1. Запуск Flower

```bash
# Запуск с monitoring профилем
docker-compose -f docker-compose.prod.yml --profile monitoring up -d flower

# Проверка статуса
docker-compose -f docker-compose.prod.yml ps flower
```

### 2. Проверка логов

```bash
docker logs fastpay-flower -f
```

---

## 🔐 Настройка аутентификации

### Переменные окружения

Создайте `.env` файл или обновите существующий:

```env
# Flower authentication
FLOWER_USER=flower
FLOWER_PASSWORD=your_secure_password_here

# Обязательно смените пароль в production!
```

### Генерация безопасного пароля

```bash
# Linux/macOS
openssl rand -base64 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Перезапуск Flower

```bash
docker-compose -f docker-compose.prod.yml --profile monitoring restart flower
```

---

## 🌐 Доступ к Flower

### Локальный доступ

```
http://localhost:5555
```

### Production доступ (через nginx)

1. Добавьте конфигурацию nginx:

```nginx
# /etc/nginx/conf.d/flower.conf
server {
    listen 80;
    server_name flower.yourdomain.com;

    auth_basic "Flower Monitoring";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://fastpay-flower:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

2. Создайте файл с паролями:

```bash
# Установите apache2-utils (если нет htpasswd)
sudo apt install apache2-utils

# Создайте файл с пользователями
htpasswd -c /etc/nginx/.htpasswd flower
# Введите пароль
```

3. Перезапустите nginx:

```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

### HTTPS доступ

```nginx
server {
    listen 443 ssl http2;
    server_name flower.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/yourdomain.crt;
    ssl_certificate_key /etc/nginx/ssl/yourdomain.key;

    auth_basic "Flower Monitoring";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://fastpay-flower:5555;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Ssl on;
    }
}
```

---

## 📊 API для управления

Flower предоставляет REST API для автоматизации:

### Получить информацию о воркерах

```bash
curl -u flower:password http://localhost:5555/api/workers
```

### Получить статистику задач

```bash
curl -u flower:password http://localhost:5555/api/tasks/stats
```

### Отменить задачу

```bash
curl -X POST -u flower:password http://localhost:5555/api/task/terminate/<task-id>
```

### Получить информацию о задаче

```bash
curl -u flower:password http://localhost:5555/api/task/info/<task-id>
```

---

## 🔧 Production конфигурация

### docker-compose.prod.yml

```yaml
flower:
  build: .
  container_name: fastpay-flower
  restart: unless-stopped
  depends_on:
    - redis
    - app
  environment:
    - CELERY_BROKER_URL=redis://redis:6379/0
    - CELERY_RESULT_BACKEND=redis://redis:6379/1
    - FLOWER_BASIC_AUTH=${FLOWER_USER}:${FLOWER_PASSWORD}
  volumes:
    - ./flower_data:/flower_data
  networks:
    - fastpay-network
  command: >
    sh -c "celery -A app.tasks.celery flower 
           --port=5555 
           --basic_auth=${FLOWER_USER}:${FLOWER_PASSWORD}
           --persistent=True
           --db=/flower_data/flower.db"
  profiles:
    - monitoring
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `FLOWER_USER` | Имя пользователя | `flower` |
| `FLOWER_PASSWORD` | Пароль | `change_me_flower` |
| `CELERY_BROKER_URL` | URL брокера | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Backend результатов | `redis://redis:6379/1` |

### Безопасность

1. **Смените пароль по умолчанию**
2. **Используйте HTTPS** в production
3. **Ограничьте доступ по IP** (nginx allow/deny)
4. **Используйте VPN** для доступа к мониторингу
5. **Регулярно обновляйте** Flower

```nginx
# Ограничение по IP
location / {
    allow 10.0.0.0/8;
    allow 192.168.1.0/24;
    deny all;
    
    proxy_pass http://fastpay-flower:5555;
    # ...
}
```

---

## 📈 Мониторинг и алерты

### Метрики Flower

Flower экспортирует метрики Prometheus:

```bash
# Доступ к метрикам
curl http://localhost:5555/metrics
```

### Интеграция с Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'flower'
    static_configs:
      - targets: ['fastpay-flower:5555']
```

### Grafana Dashboard

Импортируйте дашборд **Grafana #9368** для визуализации метрик Celery.

---

## 🛠️ Решение проблем

### Flower не запускается

```bash
# Проверьте логи
docker logs fastpay-flower

# Проверьте подключение к Redis
docker exec fastpay-flower redis-cli -h redis ping
```

### Ошибка аутентификации

```bash
# Проверьте переменные окружения
docker exec fastpay-flower env | grep FLOWER

# Перезапустите с правильными переменными
docker-compose -f docker-compose.prod.yml --profile monitoring up -d flower
```

### Задачи не отображаются

1. Проверьте подключение к Celery broker
2. Убедитесь, что `CELERY_ENABLED=true`
3. Проверьте логи воркера: `docker logs fastpay-celery-worker`

---

## 📚 Дополнительные ресурсы

- [Официальная документация Flower](https://github.com/mher/flower)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Grafana Dashboard #9368](https://grafana.com/grafana/dashboards/9368)

---

**Flower готов к использованию! 🎉**
