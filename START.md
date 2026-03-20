# 🚀 FastPay Connect — Запуск на всех платформах

> **Quick Start:** Выберите вашу платформу и следуйте инструкциям

---

## 📋 Содержание

- [Windows](#-windows)
- [macOS](#-macos)
- [Linux](#-linux)
- [Android](#-android)
- [iOS](#-ios)
- [Docker (кроссплатформенно)](#-docker)

---

## 🪟 Windows

### Быстрый старт:

1. **Дважды кликните** на `start-windows.bat`

Или вручную:

```cmd
# Установка Python (если нет)
# Скачайте с https://www.python.org/downloads/

# Клонирование
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Виртуальное окружение
python -m venv venv
venv\Scripts\activate

# Зависимости
pip install -r requirements.txt

# Настройка
copy .env.example .env
# Отредактируйте .env

# Запуск
start-windows.bat
```

### Файлы:
- 📄 `start-windows.bat` — автоматический запуск

---

## 🍎 macOS

### Быстрый старт:

```bash
# Установка зависимостей
brew install python3

# Клонирование
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости
pip3 install -r requirements.txt

# Настройка
cp .env.example .env
# Отредактируйте .env

# Запуск
chmod +x start-macos.sh
./start-macos.sh
```

### Файлы:
- 📄 `start-macos.sh` — запуск с уведомлениями
- 📄 `start.sh` — базовый скрипт (Linux/macOS)

---

## 🐧 Linux

### Быстрый старт:

```bash
# Установка Python
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Клонирование
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate

# Зависимости
pip install -r requirements.txt

# Настройка
cp .env.example .env
# Отредактируйте .env

# Запуск
chmod +x start.sh
./start.sh
```

### Файлы:
- 📄 `start.sh` — универсальный скрипт для Linux/macOS

---

## 🤖 Android

### Вариант 1: Termux (рекомендуется)

```bash
# Установка Termux из F-Droid
# https://f-droid.org/packages/com.termux/

# Обновление
pkg update && pkg upgrade

# Установка зависимостей
pkg install python postgresql redis git

# Клонирование
cd ~/storage/downloads
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Виртуальное окружение
python -m venv venv
source venv/bin/activate

# Зависимости
pip install -r requirements.txt

# Настройка
cp .env.example .env
nano .env

# Запуск
chmod +x start-android.sh
./start-android.sh
```

### Файлы:
- 📄 `start-android.sh` — скрипт для Termux
- 📄 `START_ANDROID.md` — подробная инструкция

### Вариант 2: Pydroid 3

1. Установите Pydroid 3 из Google Play
2. Откройте проект через файловый менеджер
3. Запустите `run.py`

---

## 🍏 iOS

### Вариант 1: a-Shell

```bash
# Установка a-Shell из App Store

# В приложении:
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect
pip install fastapi uvicorn pydantic sqlalchemy
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

### Вариант 2: Pythonista 3

1. Купите Pythonista 3 в App Store
2. Импортируйте проект через Git
3. Откройте `run.py` и нажмите ▶️

### Вариант 3: Облачные сервисы

Разверните на Render/Railway/Vercel (см. `START_IOS.md`)

### Файлы:
- 📄 `START_IOS.md` — подробная инструкция

---

## 🐳 Docker (кроссплатформенно)

### Требования:
- Docker Desktop (Windows/macOS/Linux)
- Docker Compose

### Быстрый старт:

```bash
# Development стек (PostgreSQL + Redis + Flower)
docker-compose -f docker-compose.dev.yml up -d

# Production стек (SQLite + Redis)
docker-compose -f docker-compose.yml up -d

# Просмотр логов
docker-compose -f docker-compose.dev.yml logs -f

# Остановка
docker-compose -f docker-compose.dev.yml down
```

### Файлы:
- 📄 `start-docker.sh` — интерактивный скрипт выбора
- 📄 `docker-compose.yml` — production конфигурация
- 📄 `docker-compose.dev.yml` — development конфигурация

### Сервисы:

| Сервис | Порт | URL |
|--------|------|-----|
| API | 8080 | http://localhost:8080 |
| Swagger UI | 8080 | http://localhost:8080/docs |
| ReDoc | 8080 | http://localhost:8080/redoc |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Flower | 5555 | http://localhost:5555 |

---

## 🔧 Переменные окружения

### Минимальная конфигурация (.env):

```env
# База данных
DATABASE_URL=sqlite:///./fastpay_connect.db

# Секретный ключ
SECRET_KEY=your_secret_key_change_in_production

# Режим
ENV=development
DEBUG=true
HOST=127.0.0.1
PORT=8080
```

### Для production:

```env
ENV=production
DEBUG=false
DATABASE_URL=postgresql://user:password@localhost:5432/fastpay
SECRET_KEY=<random_secret_64_chars>
ALLOWED_HOSTS=yourdomain.com
```

---

## ✅ Проверка работоспособности

После запуска откройте в браузере:

1. **Swagger UI**: http://localhost:8080/docs
2. **ReDoc**: http://localhost:8080/redoc
3. **Health Check**: http://localhost:8080/health

---

## 📊 Сравнение платформ

| Платформа | Сложность | Производительность | Рекомендация |
|-----------|-----------|-------------------|--------------|
| Windows | ⭐ | ⭐⭐⭐⭐ | Для разработки |
| macOS | ⭐ | ⭐⭐⭐⭐ | Для разработки |
| Linux | ⭐ | ⭐⭐⭐⭐⭐ | Для production |
| Android (Termux) | ⭐⭐⭐ | ⭐⭐ | Для тестов |
| iOS (a-Shell) | ⭐⭐⭐ | ⭐⭐ | Для тестов |
| Docker | ⭐⭐ | ⭐⭐⭐⭐ | Для production |

---

## 🆘 Решение проблем

### Python не найден:
- Windows: https://www.python.org/downloads/
- macOS: `brew install python3`
- Linux: `sudo apt install python3 python3-pip`

### Ошибка доступа к порту:
```bash
# Windows
netstat -ano | findstr :8080

# Linux/macOS
lsof -i :8080
```

### Зависимости не устанавливаются:
```bash
# Обновите pip
python -m pip install --upgrade pip

# Очистите кэш
pip cache purge

# Установите без кэша
pip install --no-cache-dir -r requirements.txt
```

### База данных не создаётся:
```bash
# Запустите миграции вручную
alembic upgrade head

# Или создайте заново
rm fastpay_connect.db  # Linux/macOS
del fastpay_connect.db  # Windows
alembic upgrade head
```

---

## 📞 Контакты

- GitHub: https://github.com/QuadDarv1ne/fastpay_connect
- Issues: https://github.com/QuadDarv1ne/fastpay_connect/issues
