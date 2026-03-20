# FastPay Connect для iOS
# =======================

## Вариант 1: a-Shell (рекомендуется)

a-Shell — это терминал для iOS с поддержкой Python и pip.

### Установка:
1. Скачайте **a-Shell** из App Store
2. Откройте приложение
3. Выполните команды:

```bash
# Клонируйте репозиторий
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect

# Установите зависимости
pip install fastapi uvicorn pydantic sqlalchemy

# Создайте .env файл
cp .env.example .env
# Отредактируйте: edit .env

# Запустите сервер
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

### Доступ:
- API: http://127.0.0.1:8080
- Swagger: http://127.0.0.1:8080/docs

---

## Вариант 2: Pythonista 3

Pythonista 3 — мощная Python IDE для iOS.

### Установка:
1. Купите **Pythonista 3** в App Store
2. Импортируйте проект через Git
3. Откройте `run.py` и нажмите ▶️

### Ограничения:
- Нет поддержки всех пакетов (Celery, Redis не работают)
- Используйте SQLite базу данных

---

## Вариант 3: Веб-приложение (PWA)

Разверните FastPay Connect на облачном сервисе:

### Render.com (бесплатно):
1. Зарегистрируйтесь на https://render.com
2. Создайте новый Web Service
3. Подключите GitHub репозиторий
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Railway.app:
1. Зарегистрируйтесь на https://railway.app
2. Нажмите "New Project" → "Deploy from GitHub"
3. Выберите репозиторий fastpay_connect
4. Добавьте переменные окружения

### Vercel:
1. Используйте `deploy/vercel.json` конфигурацию
2. Deploy через Vercel CLI:
```bash
npm install -g vercel
vercel --prod
```

---

## Вариант 4: Локальный сервер + iOS клиент

Запустите FastPay Connect на компьютере, используйте с iOS:

1. Запустите сервер на компьютере:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080
```

2. Узнайте IP компьютера в локальной сети

3. Откройте Safari на iOS:
```
http://<IP-КОМПЬЮТЕРА>:8080/docs
```

---

## Быстрый старт (a-Shell команды):

```bash
# Установка
pkg install python
pip install fastapi uvicorn pydantic sqlalchemy aiosqlite

# Запуск
cd ~/Documents/fastpay_connect
export DATABASE_URL=sqlite:///./fastpay.db
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

## Добавление на домашний экран (PWA):

1. Откройте http://localhost:8080/docs в Safari
2. Нажмите "Поделиться" → "На экран «Домой»"
3. Добавьте иконку для быстрого доступа
