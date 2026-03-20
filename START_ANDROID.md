# FastPay Connect для Android
# ===========================

## Вариант 1: Termux (рекомендуется)

Termux — мощный терминал для Android с полноценным Linux окружением.

### Установка Termux:
1. Скачайте **F-Droid** (не Google Play — там устаревшая версия)
2. Установите Termux из F-Droid: https://f-droid.org/packages/com.termux/

### Настройка Termux:
```bash
# Обновление пакетов
pkg update && pkg upgrade

# Установка Python и зависимостей
pkg install python postgresql redis git curl

# Разрешения (доступ к хранилищу)
termux-setup-storage
```

### Установка FastPay Connect:
```bash
# Клонируйте репозиторий
cd ~/storage/downloads
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Создание виртуального окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env
cp .env.example .env
nano .env  # Отредактируйте ключи API

# Запуск миграций
alembic upgrade head

# Запуск сервера
bash start-android.sh
```

### Доступ:
- API: http://127.0.0.1:8080
- Swagger: http://127.0.0.1:8080/docs

---

## Вариант 2: Pydroid 3

Pydroid 3 — Python IDE для Android с поддержкой pip.

### Установка:
1. Скачайте **Pydroid 3** из Google Play
2. Откройте приложение
3. Меню → Pip → Установите пакеты:
   ```
   fastapi
   uvicorn
   pydantic
   sqlalchemy
   aiosqlite
   ```

### Запуск:
1. Откройте файловый менеджер Pydroid
2. Найдите папку с проектом
3. Откройте `run.py`
4. Нажмите кнопку Play ▶️

### Ограничения:
- Нет поддержки Celery и Redis
- Используйте SQLite базу данных

---

## Вариант 3: Docker на Android

Для Android с root-правами или через Termux:

```bash
# Установка Docker в Termux
pkg install docker

# Или используйте UserLAnd приложение из Play Store

# Запуск через docker-compose
cd fastpay_connect
docker-compose -f docker-compose.dev.yml up -d
```

---

## Вариант 4: Веб-сервисы (без установки)

Разверните на облачном сервисе:

### Render.com:
1. https://render.com → New Web Service
2. Connect GitHub → fastpay_connect
3. Build: `pip install -r requirements.txt`
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Railway.app:
1. https://railway.app → New Project
2. Deploy from GitHub
3. Автоматический деплой при push

---

## Быстрый старт (Termux):

```bash
# Одна команда для установки
pkg update && pkg install python postgresql redis git
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Запуск
bash start-android.sh
```

## Ярлык на домашнем экране:

Создайте файл `~/.shortcuts/fastpay` в Termux:
```bash
#!/data/data/com.termux/files/usr/bin/bash
cd ~/storage/downloads/fastpay_connect
source venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Сделайте исполняемым:
```bash
chmod +x ~/.shortcuts/fastpay
```

Добавьте ярлык через Termux:Widget приложение.

---

## Отладка через ADB:

```bash
# Проброс портов с устройства на ПК
adb reverse tcp:8080 tcp:8080

# Теперь доступно на ПК
http://localhost:8080/docs
```
