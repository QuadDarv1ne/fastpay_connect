# 📦 Cloudflare Deployment Guide

Полное руководство по развёртыванию FastPay Connect на Cloudflare.

## 📋 Содержание

1. [Обзор](#обзор)
2. [Cloudflare Workers](#cloudflare-workers)
3. [Cloudflare Pages](#cloudflare-pages)
4. [GitHub Actions](#github-actions)
5. [Мониторинг](#мониторинг)

---

## 📖 Обзор

Cloudflare предоставляет несколько способов развёртывания:

| Продукт | Назначение | Python |
|---------|-----------|--------|
| **Workers** | Edge функции | ❌ (JS/TS/WASM) |
| **Pages** | Статический хостинг | ❌ |
| **Workers + Proxy** | Проксирование к backend | ✅ |

**Рекомендация:** Используйте Workers как прокси для вашего Python backend.

---

## ☁️ Cloudflare Workers

### Что такое Workers?

Cloudflare Workers — serverless функции, работающие на edge-серверах Cloudflare.

### Архитектура

```
Клиент → Cloudflare Worker → Ваш Python Backend
           ├─ Rate Limiting
           ├─ Кэширование
           ├─ CORS
           └─ Защита от DDoS
```

### Быстрый старт

#### 1. Установка Wrangler CLI

```bash
# Через npm
npm install -g wrangler

# Через yarn
yarn global add wrangler

# Проверка установки
wrangler --version
```

#### 2. Авторизация

```bash
wrangler login
```

Откроется браузер для авторизации через Cloudflare аккаунт.

#### 3. Настройка wrangler.toml

```toml
name = "fastpay-connect"
main = "worker.ts"
compatibility_date = "2024-01-01"

[vars]
API_URL = "https://your-fastpay-api.com"
ALLOWED_ORIGINS = "*"
RATE_LIMIT = "100"
```

#### 4. Локальная разработка

```bash
wrangler dev
```

Worker запустится на `http://localhost:8787`

#### 5. Деплой

```bash
# Production
wrangler deploy

# С флагом dry-run (проверка)
wrangler deploy --dry-run

# Деплой в staging окружение
wrangler deploy --env staging
```

---

## 📄 Cloudflare Pages

### Что такое Pages?

Cloudflare Pages — платформа для хостинга статических сайтов и JAMstack приложений.

### Использование с FastPay Connect

Pages можно использовать для:
- Хостинга статических файлов (CSS, JS, изображения)
- Проксирования API через Functions

### Деплой статических файлов

```bash
# Создание директории public
mkdir -p public

# Копирование статики
cp -r app/static/* public/

# Деплой
wrangler pages deploy public --project-name=fastpay-connect
```

### Pages Functions

Создайте файл `functions/api/[[path]].ts`:

```typescript
export async function onRequest(context) {
  const { request, env } = context;
  const apiUrl = env.API_URL;
  
  // Проксирование к backend
  return fetch(new URL(request.url, apiUrl));
}
```

---

## 🔄 GitHub Actions

### Автоматический деплой

1. **Настройте secrets в репозитории:**

```
Settings → Secrets and variables → Actions

- CLOUDFLARE_API_TOKEN
- CLOUDFLARE_ACCOUNT_ID
```

2. **Создайте токен Cloudflare:**

```
Cloudflare Dashboard → Profile → API Tokens
Create Token → Edit Cloudflare Workers
```

3. **Workflow автоматически задеплоит при push в main**

### Ручной триггер

```yaml
# .github/workflows/deploy-cloudflare-manual.yml
name: Manual Cloudflare Deploy

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment'
        required: true
        default: 'production'
        type: choice
        options:
        - production
        - staging

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          environment: ${{ inputs.environment }}
```

---

## 📊 Мониторинг

### Логи в реальном времени

```bash
# Просмотр логов
wrangler tail

# С фильтрацией
wrangler tail --status error

# По конкретному Worker
wrangler tail --name fastpay-connect
```

### Метрики

```bash
# Общая статистика
wrangler metrics

# По конкретному Worker
wrangler metrics --name fastpay-connect
```

### Alerts

Настройте в Cloudflare Dashboard:
1. Workers & Pages → fastpay-connect
2. Analytics → Create Alert

Доступные метрики:
- Requests
- Errors
- CPU Time
- Response Time

---

## 🔧 Конфигурация

### Переменные окружения

```toml
# wrangler.toml

[vars]
API_URL = "https://api.example.com"
ALLOWED_ORIGINS = "https://example.com"
RATE_LIMIT = "100"

# Environment-specific
[env.production.vars]
API_URL = "https://api.production.example.com"

[env.staging.vars]
API_URL = "https://api.staging.example.com"
```

### KV Storage

```bash
# Создание namespace
wrangler kv:namespace create "RATE_LIMIT_KV"

# Выведет ID, скопируйте в wrangler.toml:
[[kv_namespaces]]
binding = "RATE_LIMIT_KV"
id = "your-namespace-id"
```

### D1 Database

```bash
# Создание базы
wrangler d1 create fastpay-db

# Миграции
wrangler d1 migrations create fastpay-db create_users

# Применение
wrangler d1 migrations apply fastpay-db
```

---

## 🚀 Production Checklist

- [ ] Настроены переменные окружения
- [ ] Создан KV namespace для rate limiting
- [ ] Настроен CORS для вашего домена
- [ ] Включён Workers Analytics
- [ ] Настроены alerts
- [ ] Добавлен кастомный домен
- [ ] Включён Automatic HTTPS
- [ ] Настроен Backup конфигурации

---

## 🛡️ Безопасность

### Rate Limiting

Worker автоматически ограничивает запросы:

```typescript
// worker.ts
const RATE_LIMIT = 100; // запросов в минуту
```

### CORS

```typescript
// Разрешить только ваш домен
const ALLOWED_ORIGINS = "https://your-domain.com";
```

### DDoS Protection

Cloudflare автоматически защищает от DDoS атак.

### WAF Rules

Настройте в Cloudflare Dashboard:
1. Security → WAF
2. Create Rule

Примеры правил:
- Блокировка по стране
- Rate limiting по IP
- Блокировка известных ботов

---

## 💰 Стоимость

### Бесплатный тариф

- 100,000 запросов/день
- 10ms CPU time
- 1 KV namespace

### Paid тарифы

| План | Цена | Запросы | CPU Time |
|------|------|---------|----------|
| **Workers Paid** | $5/мес | 10M | 10s |
| **Business** | $200/мес | Unlimited | Unlimited |

---

## 🆘 Troubleshooting

### Ошибка: "Authentication required"

```bash
wrangler login
```

### Ошибка: "Invalid API URL"

Проверьте `wrangler.toml`:
```toml
[vars]
API_URL = "https://correct-url.com"
```

### Ошибка: "KV namespace not found"

Создайте namespace и добавьте ID в `wrangler.toml`.

### Worker не проксирует запросы

Проверьте логи:
```bash
wrangler tail --status error
```

---

## 📞 Поддержка

- **Документация:** https://developers.cloudflare.com/workers/
- **Discord:** https://discord.gg/cloudflaredev
- **Forum:** https://community.cloudflare.com/

---

## 📝 Примеры использования

### Кэширование ответов

```typescript
async function fetchWithCache(request: Request, url: string) {
  const cache = caches.default;
  const response = await fetch(url);
  
  if (response.ok) {
    const cachingResponse = new Response(response.body, {
      headers: {
        ...response.headers,
        'Cache-Control': 'public, max-age=300'
      }
    });
    ctx.waitUntil(cache.put(request, cachingResponse.clone()));
  }
  
  return response;
}
```

### Rate Limiting с KV

```typescript
async function checkRateLimit(key: string, limit: number) {
  const count = await RATE_LIMIT_KV.get(key) || 0;
  
  if (parseInt(count) >= limit) {
    return { allowed: false };
  }
  
  await RATE_LIMIT_KV.put(key, (parseInt(count) + 1).toString(), {
    expirationTtl: 60
  });
  
  return { allowed: true };
}
```

---

## 📚 Дополнительные ресурсы

- [Wrangler Documentation](https://developers.cloudflare.com/workers/wrangler/)
- [Workers Examples](https://github.com/cloudflare/workers-sdk/tree/main/templates)
- [KV Storage Guide](https://developers.cloudflare.com/kv/)
- [D1 Database Guide](https://developers.cloudflare.com/d1/)
