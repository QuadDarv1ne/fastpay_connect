# 📦 Руководство по деплою FastPay Connect

Это руководство содержит инструкции по развёртыванию FastPay Connect на различных платформах.

## 📋 Содержание

1. [Локальная разработка](#локальная-разработка)
2. [Docker](#docker)
3. [Render](#render)
4. [Railway](#railway)
5. [Fly.io](#flyio)
6. [Heroku](#heroku)
7. [Google Cloud Run](#google-cloud-run)
8. [AWS Elastic Beanstalk](#aws-elastic-beanstalk)
9. [Kubernetes](#kubernetes)
10. [Cloudflare Workers](#cloudflare-workers)
11. [Cloudflare Pages](#cloudflare-pages)
12. [VPS (Ubuntu/Debian)](#vps-ubuntudebian)

---

## 🚀 Локальная разработка

### Быстрый старт

```bash
# Установка зависимостей
pip install -r requirements.txt

# Копирование .env.example в .env
cp .env.example .env

# Заполните .env вашими ключами

# Запуск миграций
alembic upgrade head

# Запуск приложения
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Использование Makefile

```bash
make help          # Показать все команды
make dev           # Запуск в режиме разработки
make test          # Запуск тестов
make docker-up     # Запуск Docker Compose
make deploy        # Деплой на production
```

---

## 🐳 Docker

### Production Docker Compose

```bash
# Копирование .env.example
cp .env.example .env

# Запуск всех сервисов (PostgreSQL, App, Nginx, Redis)
docker-compose -f docker-compose.prod.yml up -d

# Просмотр логов
docker-compose -f docker-compose.prod.yml logs -f

# Остановка
docker-compose -f docker-compose.prod.yml down
```

### Переменные окружения

Создайте файл `.env` на основе `.env.example`:

```bash
# База данных
DATABASE_URL=postgresql://fastpay_user:password@db:5432/fastpay_connect

# Секретные ключи
SECRET_KEY=your_secret_key_here

# API ключи платёжных систем
YOOKASSA_API_KEY=your_yookassa_api_key
YOOKASSA_SECRET_KEY=your_yookassa_secret_key
# ... остальные ключи
```

---

## 🎨 Render

### Автоматический деплой

1. Зарегистрируйтесь на [Render](https://render.com)
2. Нажмите "New +" → "Web Service"
3. Подключите ваш GitHub репозиторий
4. Настройте параметры:
   - **Name:** fastpay-connect
   - **Environment:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Переменные окружения

Добавьте в настройках сервиса:

```
PYTHON_VERSION=3.11.0
DATABASE_URL=postgresql://...
SECRET_KEY=your_secret_key
# ... остальные переменные
```

### Использование render.yaml

```bash
# Деплой с помощью Render CLI
renderctl deploy --name fastpay-connect
```

---

## 🚂 Railway

### Быстрый деплой

1. Установите Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Войдите в аккаунт:
   ```bash
   railway login
   ```

3. Инициализируйте проект:
   ```bash
   railway init
   ```

4. Задеплойте:
   ```bash
   railway up
   ```

### База данных

```bash
# Создание PostgreSQL базы
railway add postgresql

# Просмотр connection string
railway variables
```

---

## 🪂 Fly.io

### Установка CLI

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

### Деплой

```bash
# Инициализация приложения
fly launch --name fastpay-connect

# Деплой
fly deploy

# Открыть приложение
fly open
```

### Масштабирование

```bash
fly scale count 3  # 3 инстанса
fly scale vm shared-cpu-2x  # Более мощный тариф
```

---

## 🟣 Heroku

### Установка CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Ubuntu/Debian
curl https://cli-assets.heroku.com/install.sh | sh
```

### Деплой

```bash
# Вход в аккаунт
heroku login

# Создание приложения
heroku create fastpay-connect

# Добавление PostgreSQL
heroku addons:create heroku-postgresql:mini

# Деплой
git push heroku main

# Запуск миграций
heroku run alembic upgrade head

# Открыть приложение
heroku open
```

### Переменные окружения

```bash
heroku config:set SECRET_KEY=your_secret_key
heroku config:set YOOKASSA_API_KEY=your_key
# ... остальные переменные
```

---

## ☁️ Google Cloud Run

### Подготовка

```bash
# Установка gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Вход в аккаунт
gcloud auth login

# Установка проекта
gcloud config set project YOUR_PROJECT_ID
```

### Деплой

```bash
# Сборка и деплой
gcloud builds submit --tag gcr.io/PROJECT_ID/fastpay-connect

gcloud run deploy fastpay-connect \
  --image gcr.io/PROJECT_ID/fastpay-connect \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="SECRET_KEY=your_key,DATABASE_URL=postgresql://..."
```

### Автоматический деплой через Cloud Build

```bash
# Использование cloudbuild.yaml
gcloud builds submit --config cloudbuild.yaml
```

---

## 📦 AWS Elastic Beanstalk

### Установка EB CLI

```bash
pip install awsebcli
```

### Инициализация

```bash
eb init -p python-3.11 fastpay-connect --region us-east-1
eb create production
```

### Деплой

```bash
eb deploy
```

### Переменные окружения

```bash
eb setenv SECRET_KEY=your_secret_key
eb setenv DATABASE_URL=postgresql://...
```

### Мониторинг

```bash
eb status
eb health
eb logs
```

---

## ☸️ Kubernetes

### Требования

- Kubernetes кластер (GKE, EKS, AKS, minikube)
- kubectl настроенный на кластер
- Helm (опционально)

### Деплой

```bash
# Применение конфигурации
kubectl apply -f k8s/deployment.yaml

# Проверка статуса
kubectl get pods -n fastpay
kubectl get svc -n fastpay

# Просмотр логов
kubectl logs -n fastpay -l app=fastpay -f
```

### Масштабирование

```bash
kubectl scale deployment fastpay-app --replicas=5 -n fastpay
```

### Обновление

```bash
kubectl rollout restart deployment/fastpay-app -n fastpay
kubectl rollout status deployment/fastpay-app -n fastpay
```

### Откат

```bash
kubectl rollout undo deployment/fastpay-app -n fastpay
```

---

## ☁️ Cloudflare Workers

Cloudflare Workers позволяет запускать JavaScript/TypeScript код на edge-серверах Cloudflare.
Для Python приложения Workers используется как прокси для кэширования, rate limiting и защиты.

### Требования

- Аккаунт Cloudflare
- Установленный Node.js и npm
- Wrangler CLI

### Установка Wrangler

```bash
npm install -g wrangler
wrangler login
```

### Настройка

1. Откройте `wrangler.toml` и укажите ваш API URL:

```toml
name = "fastpay-connect"
main = "worker.ts"

[vars]
API_URL = "https://your-fastpay-api.com"
```

2. Создайте KV namespace для rate limiting:

```bash
wrangler kv:namespace create "RATE_LIMIT_KV"
```

3. Скопируйте ID из вывода и вставьте в `wrangler.toml`.

### Деплой

```bash
# Development
wrangler dev

# Production
wrangler deploy
```

### Деплой через GitHub Actions

```bash
# Установите secrets в репозитории:
# - CLOUDFLARE_API_TOKEN
# - CLOUDFLARE_ACCOUNT_ID

# Workflow автоматически задеплоит при push в main
```

### Функции

- **Rate Limiting**: Ограничение запросов через KV storage
- **Кэширование**: Кэширование статических ответов
- **CORS**: Управление CORS заголовками
- **Проксирование**: Все запросы перенаправляются на backend

### Мониторинг

```bash
# Просмотр логов в реальном времени
wrangler tail

# Просмотр метрик
wrangler metrics
```

---

## 📄 Cloudflare Pages

Cloudflare Pages — хостинг для статических сайтов и JAMstack.

### Требования

- Аккаунт Cloudflare
- GitHub репозиторий

### Деплой через Dashboard

1. Зайдите на [Cloudflare Pages](https://pages.cloudflare.com/)
2. Нажмите "Create a project"
3. Подключите GitHub репозиторий
4. Настройте build:
   - **Build command**: `echo "No build needed"`
   - **Build output directory**: `app/static`
5. Нажмите "Deploy"

### Деплой через CLI

```bash
# Установка зависимостей
npm ci

# Деплой
wrangler pages deploy public --project-name=fastpay-connect
```

### Переменные окружения

Добавьте в настройках проекта Pages:

```
API_URL=https://your-fastpay-api.com
ALLOWED_ORIGINS=https://your-domain.com
```

---

## 🖥️ VPS (Ubuntu/Debian)

### Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
sudo apt install -y python3-pip python3-venv postgresql nginx docker.io docker-compose

# Создание пользователя
sudo adduser fastpay
sudo usermod -aG docker fastpay
```

### Настройка PostgreSQL

```bash
sudo -u postgres psql
CREATE DATABASE fastpay_connect;
CREATE USER fastpay_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fastpay_connect TO fastpay_user;
\q
```

### Установка приложения

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/fastpay_connect.git
cd fastpay_connect

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env
cp .env.example .env
# Отредактируйте .env

# Запуск миграций
alembic upgrade head
```

### Systemd сервис

Создайте файл `/etc/systemd/system/fastpay.service`:

```ini
[Unit]
Description=FastPay Connect API
After=network.target postgresql.service

[Service]
User=fastpay
Group=fastpay
WorkingDirectory=/home/fastpay/fastpay_connect
Environment="PATH=/home/fastpay/fastpay_connect/venv/bin"
ExecStart=/home/fastpay/fastpay_connect/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Запуск сервиса
sudo systemctl daemon-reload
sudo systemctl enable fastpay
sudo systemctl start fastpay
sudo systemctl status fastpay
```

### Настройка Nginx

```bash
# Копирование конфигурации
sudo cp nginx/conf.d/fastpay.conf /etc/nginx/sites-available/fastpay
sudo ln -s /etc/nginx/sites-available/fastpay /etc/nginx/sites-enabled/

# Проверка и перезапуск
sudo nginx -t
sudo systemctl restart nginx
```

### SSL сертификат (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d fastpay.example.com
```

---

## 🔒 Безопасность

### Рекомендации

1. **Никогда не коммитьте `.env` файлы**
2. **Используйте secrets manager** (AWS Secrets Manager, HashiCorp Vault)
3. **Включите HTTPS** на production
4. **Настройте firewall** (UFW, iptables)
5. **Регулярно обновляйте зависимости**
6. **Мониторьте логи** на предмет атак

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## 📊 Мониторинг

### Prometheus + Grafana

```bash
# Добавление метрик в приложение
pip install prometheus-client

# Endpoint /metrics уже доступен
curl http://localhost:8080/metrics
```

### Логи

```bash
# Просмотр логов приложения
tail -f logs/app.log
tail -f logs/error.log

# Docker логи
docker-compose logs -f app
```

---

## 🆘 Troubleshooting

### Приложение не запускается

```bash
# Проверка логов
docker-compose logs app
journalctl -u fastpay -f

# Проверка переменных окружения
printenv | grep FASTPAY
```

### Ошибки базы данных

```bash
# Проверка подключения
psql $DATABASE_URL

# Запуск миграций вручную
alembic upgrade head
```

### Проблемы с SSL

```bash
# Обновление сертификата
sudo certbot renew

# Проверка
sudo nginx -t
```

---

## 📞 Поддержка

- **Документация:** `/docs` (Swagger UI)
- **Health Check:** `/health`
- **Readiness:** `/ready`

---

## 📝 Лицензия

MIT License - см. файл LICENSE
