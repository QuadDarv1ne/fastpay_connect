# 📦 Файлы деплоя FastPay Connect

В этой папке находятся все конфигурационные файлы для развёртывания на различных платформах.

## 📁 Структура

```
deploy/
├── README.md                      # Этот файл
├── Makefile                       # Автоматизация задач
├── Procfile                       # Heroku/Railway команды
├── render.yaml                    # Render конфигурация
├── railway.json                   # Railway конфигурация
├── fly.toml                       # Fly.io конфигурация
├── vercel.json                    # Vercel конфигурация
├── netlify.toml                   # Netlify конфигурация
│
├── cloudflare/                    # Cloudflare Workers/Pages
│   ├── wrangler.toml              # Wrangler конфигурация
│   ├── worker.ts                  # Worker код
│   ├── package.json               # Node.js зависимости
│   ├── tsconfig.json              # TypeScript конфигурация
│   ├── deploy-cloudflare-workers.yml
│   └── deploy-cloudflare-pages.yml
│
├── k8s/                           # Kubernetes
│   └── deployment.yaml            # Kubernetes манифесты
│
├── aws/                           # AWS Elastic Beanstalk
│   ├── .ebextensions/
│   │   └── 01_python.config
│   └── .platform/
│       └── nginx/
│           ├── nginx.conf
│           └── conf.d/
│               └── 01_fastpay.conf
│
├── gcp/                           # Google Cloud Platform
│   └── cloudbuild.yaml            # Cloud Build конфигурация
│
├── nginx/                         # Nginx конфигурация
│   ├── nginx.conf                 # Основная конфигурация
│   └── conf.d/
│       └── fastpay.conf           # Конфигурация сайта
│
└── scripts/                       # Скрипты деплоя
    ├── deploy.sh                  # Bash скрипт деплоя
    └── init-db.sql                # Инициализация БД
```

---

## 🚀 Быстрый старт

### Render

```bash
cd deploy
# Подключите репозиторий на https://render.com
# render.yaml будет использован автоматически
```

### Railway

```bash
cd deploy
railway login
railway up
```

### Fly.io

```bash
cd deploy
fly launch --name fastpay-connect
fly deploy
```

### Cloudflare Workers

```bash
cd deploy/cloudflare
npm install
wrangler login
wrangler deploy
```

### Kubernetes

```bash
kubectl apply -f deploy/k8s/deployment.yaml
```

---

## 📋 Описание файлов

### Основные платформы

| Файл | Платформа | Назначение |
|------|-----------|------------|
| `render.yaml` | Render | Full-stack деплой с БД |
| `railway.json` | Railway | Конфигурация деплоя |
| `fly.toml` | Fly.io | Деплой на Edge |
| `vercel.json` | Vercel | Serverless функции |
| `netlify.toml` | Netlify | Статический хостинг |
| `Procfile` | Heroku | Команды запуска |
| `Makefile` | Все | Автоматизация задач |

### Cloudflare

| Файл | Назначение |
|------|------------|
| `wrangler.toml` | Конфигурация Workers |
| `worker.ts` | TypeScript код прокси |
| `package.json` | Node.js зависимости |
| `tsconfig.json` | TypeScript настройки |

### Kubernetes

| Файл | Назначение |
|------|------------|
| `deployment.yaml` | Манифесты K8s (Deployment, Service, Ingress, HPA) |

### AWS

| Файл | Назначение |
|------|------------|
| `.ebextensions/01_python.config` | Настройки Elastic Beanstalk |
| `.platform/nginx/` | Nginx конфигурация для EB |

### Google Cloud

| Файл | Назначение |
|------|------------|
| `cloudbuild.yaml` | Cloud Build + Cloud Run |

### Nginx

| Файл | Назначение |
|------|------------|
| `nginx/nginx.conf` | Основная конфигурация |
| `nginx/conf.d/fastpay.conf` | Конфигурация сайта |

### Скрипты

| Файл | Назначение |
|------|------------|
| `scripts/deploy.sh` | Bash скрипт деплоя на VPS |
| `scripts/init-db.sql` | Инициализация PostgreSQL |

---

## 🔧 Использование Makefile

```bash
cd deploy

make help              # Показать все команды
make dev               # Запуск в режиме разработки
make test              # Запуск тестов
make docker-up         # Запуск Docker Compose
make deploy-render     # Деплой на Render
make deploy-railway    # Деплой на Railway
make deploy-flyio      # Деплой на Fly.io
make deploy-k8s        # Деплой на Kubernetes
make health            # Проверка здоровья
```

---

## 📖 Документация

- [DEPLOYMENT.md](../DEPLOYMENT.md) — Полное руководство по деплою
- [CLOUDFLARE_DEPLOY.md](../CLOUDFLARE_DEPLOY.md) — Cloudflare Workers/Pages
- [README.md](../README.md) — Основная документация проекта

---

## 🔐 Secrets

Для автоматического деплоя через GitHub Actions настройте secrets:

```
Settings → Secrets and variables → Actions

# Cloudflare
- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID

# Render
- RENDER_API_KEY

# Railway
- RAILWAY_TOKEN
- RAILWAY_PROJECT_ID

# Fly.io
- FLY_API_TOKEN

# Kubernetes
- KUBE_CONFIG

# VPS
- VPS_HOST
- VPS_USERNAME
- VPS_SSH_KEY
- VPS_PORT
```

---

## 🆘 Troubleshooting

### Ошибка: "wrangler.toml not found"

Убедитесь, что запускаете команды из папки `deploy/cloudflare/`:

```bash
cd deploy/cloudflare
wrangler deploy
```

### Ошибка: "fly.toml not found"

Запускайте flyctl из папки deploy:

```bash
cd deploy
flyctl deploy
```

### Ошибка: "k8s/deployment.yaml not found"

Путь к файлу изменился:

```bash
# Было
kubectl apply -f k8s/deployment.yaml

# Стало
kubectl apply -f deploy/k8s/deployment.yaml
```

---

## 📝 Лицензия

MIT License — см. файл LICENSE в корне проекта
