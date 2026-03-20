@echo off
REM FastPay Connect - Запуск сервера для Windows
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ============================================
echo   FastPay Connect - Payment Gateway API
echo   Windows Launch Script
echo ============================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден! Установите Python 3.10+
    echo Скачать: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python найден
python --version

REM Проверка виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Активация виртуального окружения...
    call venv\Scripts\activate.bat
) else (
    echo [WARN] Виртуальное окружение не найдено
    echo [INFO] Установка зависимостей...
    pip install -r requirements.txt
)

REM Проверка .env файла
if not exist ".env" (
    echo [WARN] Файл .env не найден
    if exist ".env.example" (
        echo [INFO] Копирование .env.example в .env
        copy .env.example .env
        echo [ACTION] Отредактируйте .env и заполните ключи API
    ) else (
        echo [ERROR] Файл .env.example не найден!
        pause
        exit /b 1
    )
)

REM Создание директорий
if not exist "logs" mkdir logs
if not exist "app\static" mkdir app\static

REM Проверка базы данных
echo [INFO] Проверка базы данных...
python -c "from app.database import init_db; init_db()" 2>nul
if errorlevel 1 (
    echo [WARN] Не удалось инициализировать базу данных
    echo [INFO] Запуск миграций Alembic...
    alembic upgrade head
)

REM Запуск сервера
echo.
echo ============================================
echo   Запуск сервера FastPay Connect
echo   URL: http://127.0.0.1:8080
echo   Docs: http://127.0.0.1:8080/docs
echo ============================================
echo.

set HOST=%HOST:127.0.0.1%
set PORT=%PORT:8080%
set ENV=%ENV:development%

python -m uvicorn app.main:app --host %HOST% --port %PORT% --reload

pause
