#!/bin/bash
# FastPay Connect - Запуск сервера для macOS/Linux
# ================================================

set -e

echo ""
echo "============================================"
echo "  FastPay Connect - Payment Gateway API"
echo "  macOS/Linux Launch Script"
echo "============================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 не найден! Установите Python 3.10+"
    echo "macOS: brew install python3"
    echo "Linux: sudo apt install python3 python3-pip"
    exit 1
fi

echo "[OK] Python найден"
python3 --version

# Проверка виртуального окружения
if [ -d "venv" ]; then
    echo "[INFO] Активация виртуального окружения..."
    source venv/bin/activate
else
    echo "[WARN] Виртуальное окружение не найдено"
    echo "[INFO] Установка зависимостей..."
    python3 -m pip install -r requirements.txt
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "[WARN] Файл .env не найден"
    if [ -f ".env.example" ]; then
        echo "[INFO] Копирование .env.example в .env"
        cp .env.example .env
        echo "[ACTION] Отредактируйте .env и заполните ключи API"
    else
        echo "[ERROR] Файл .env.example не найден!"
        exit 1
    fi
fi

# Создание директорий
mkdir -p logs app/static

# Проверка/создание базы данных
echo "[INFO] Проверка базы данных..."
python3 -c "from app.database import init_db; init_db()" 2>/dev/null || {
    echo "[WARN] Не удалось инициализировать базу данных"
    echo "[INFO] Запуск миграций Alembic..."
    alembic upgrade head
}

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "============================================"
echo -e "  ${GREEN}Запуск сервера FastPay Connect${NC}"
echo -e "  ${BLUE}URL:${NC} http://127.0.0.1:8080"
echo -e "  ${BLUE}Docs:${NC} http://127.0.0.1:8080/docs"
echo "============================================"
echo ""

# Переменные окружения
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8080}"
export ENV="${ENV:-development}"

# Запуск сервера
python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
