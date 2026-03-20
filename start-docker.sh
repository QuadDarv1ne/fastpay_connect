#!/bin/bash
# FastPay Connect - Docker Compose Launcher
# ==========================================
# Для всех платформ с Docker Desktop

set -e

echo ""
echo "============================================"
echo "  FastPay Connect - Docker Compose"
echo "  Cross-Platform Launch Script"
echo "============================================"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker не найден!"
    echo "Установите Docker Desktop: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "[OK] Docker найден"
docker --version

# Проверка Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[ERROR] Docker Compose не найден!"
    exit 1
fi

# Определение версии Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker compose"
fi

echo "[OK] Docker Compose найден"

# Меню выбора режима
echo ""
echo "Выберите режим запуска:"
echo "  1) Development (PostgreSQL + Redis + Flower)"
echo "  2) Production (SQLite + Redis)"
echo "  3) Только база данных (PostgreSQL)"
echo "  4) Остановить все сервисы"
echo "  5) Просмотр логов"
echo ""
read -p "Ваш выбор [1-5]: " choice

case $choice in
    1)
        echo "[INFO] Запуск development стека..."
        $COMPOSE_CMD -f docker-compose.dev.yml up -d
        echo "[OK] Сервисы запущены!"
        echo ""
        echo "============================================"
        echo "  Сервисы доступны:"
        echo "  - API: http://localhost:8080"
        echo "  - Swagger: http://localhost:8080/docs"
        echo "  - Flower: http://localhost:5555"
        echo "  - PostgreSQL: localhost:5432"
        echo "  - Redis: localhost:6379"
        echo "============================================"
        ;;
    2)
        echo "[INFO] Запуск production стека..."
        $COMPOSE_CMD -f docker-compose.yml up -d
        echo "[OK] Сервисы запущены!"
        echo ""
        echo "============================================"
        echo "  Сервисы доступны:"
        echo "  - API: http://localhost:8080"
        echo "  - Swagger: http://localhost:8080/docs"
        echo "============================================"
        ;;
    3)
        echo "[INFO] Запуск только базы данных..."
        $COMPOSE_CMD -f docker-compose.dev.yml up -d db redis
        echo "[OK] База данных запущена!"
        ;;
    4)
        echo "[INFO] Остановка всех сервисов..."
        $COMPOSE_CMD -f docker-compose.dev.yml down
        $COMPOSE_CMD -f docker-compose.yml down
        echo "[OK] Сервисы остановлены!"
        ;;
    5)
        echo "[INFO] Просмотр логов..."
        $COMPOSE_CMD -f docker-compose.dev.yml logs -f
        ;;
    *)
        echo "[ERROR] Неверный выбор"
        exit 1
        ;;
esac
