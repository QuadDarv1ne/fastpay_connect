#!/data/data/com.termux/files/usr/bin/bash
# FastPay Connect - Запуск для Android (Termux)
# ==============================================
# Установка: pkg install python postgresql redis
# https://termux.dev/

set -e

echo ""
echo "============================================"
echo "  FastPay Connect - Android (Termux)"
echo "============================================"
echo ""

# Проверка Python
if ! command -v python &> /dev/null; then
    echo "[ERROR] Python не найден!"
    echo "Установите: pkg install python"
    exit 1
fi

echo "[OK] Python найден"
python --version

# Установка зависимостей (первый запуск)
if [ ! -d ".venv" ]; then
    echo "[INFO] Создание виртуального окружения..."
    python -m venv .venv
fi

source .venv/bin/activate

echo "[INFO] Установка зависимостей..."
pip install -r requirements.txt --quiet

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "[WARN] Файл .env не найден"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[ACTION] Отредактируйте .env: nano .env"
    fi
fi

# Создание директорий
mkdir -p logs app/static

# Запуск сервера
echo ""
echo "============================================"
echo "  Запуск FastPay Connect на Android"
echo "  URL: http://127.0.0.1:8080"
echo "============================================"
echo ""

export HOST="127.0.0.1"
export PORT="8080"
export ENV="development"

python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
