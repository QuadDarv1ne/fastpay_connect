#!/bin/bash
# FastPay Connect - Запуск для macOS (App Bundle)
# ================================================
# Запуск как нативное приложение macOS

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo ""
echo "============================================"
echo "  FastPay Connect - macOS App"
echo "============================================"
echo ""

# Проверка на наличие Python.app
if [ -d "/Applications/Python3.10" ] || [ -d "/Applications/Python3.11" ] || [ -d "/Applications/Python3.12" ]; then
    PYTHON_CMD="/usr/bin/python3"
else
    PYTHON_CMD="python3"
fi

# Проверка Python
if ! command -v $PYTHON_CMD &> /dev/null; then
    osascript -e 'display alert "Python не найден!" message "Установите Python 3.10+ с python.org или Homebrew"'
    exit 1
fi

# Активация venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Установка зависимостей если нужно
pip install -q -r requirements.txt

# Создание .env если нет
if [ ! -f ".env" ]; then
    cp .env.example .env 2>/dev/null || true
fi

# Создание директорий
mkdir -p logs app/static

# Уведомление о запуске
osascript -e 'display notification "Запуск FastPay Connect..." with title "FastPay Connect"' &

# Запуск сервера в фоне
export HOST="127.0.0.1"
export PORT="8080"

echo "Запуск сервера..."
echo "URL: http://127.0.0.1:8080"
echo "Docs: http://127.0.0.1:8080/docs"
echo ""
echo "Нажмите Ctrl+C для остановки"

python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
