# FastPay Connect PWA (Progressive Web App)

**Версия:** 1.0.0  
**Автор:** Dupley Maxim Igorevich  
**Дата:** Март 2026

## 📱 Обзор

FastPay Connect теперь поддерживает PWA (Progressive Web App) - технологию, которая позволяет устанавливать веб-приложение на устройство пользователя и работать с ним как с нативным приложением.

## ✨ Возможности PWA

### Основные преимущества

| Возможность | Описание |
|-------------|----------|
| 📴 **Офлайн режим** | Работа без подключения к интернету с кэшированием данных |
| 🔔 **Push-уведомления** | Мгновенные уведомления о новых платежах и webhook-ах |
| 🚀 **Быстрая загрузка** | Кэширование статических ресурсов для мгновенной загрузки |
| 📱 **Адаптивность** | Оптимальное отображение на любом устройстве |
| 🔄 **Автообновление** | Автоматическое обновление при наличии новой версии |
| 🔒 **Безопасность** | HTTPS соединение и безопасное хранение данных |
| 🏠 **На главный экран** | Установка на главный экран без магазина приложений |

## 🚀 Быстрый старт

### 1. Запуск сервера

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Открыть PWA страницу

Перейдите по адресу: `http://localhost:8000/pwa`

### 3. Установка приложения

#### Desktop (Chrome/Edge)
1. Откройте `http://localhost:8000/pwa`
2. Нажмите кнопку "Установить приложение"
3. Подтвердите установку в диалоге браузера

#### Android (Chrome)
1. Откройте сайт в Chrome
2. Нажмите меню (⋮) → "Установить приложение"
3. Или: "Добавить на главный экран"

#### iOS (Safari)
1. Откройте сайт в Safari
2. Нажмите кнопку "Поделиться"
3. Выберите "На экран «Домой»"

## 📁 Структура файлов PWA

```
app/
├── static/
│   ├── manifest.json           # Конфигурация PWA
│   ├── service-worker.js       # Service Worker для офлайн-режима
│   ├── icons/
│   │   ├── icon-72x72.png      # Иконки разных размеров
│   │   ├── icon-96x96.png
│   │   ├── icon-128x128.png
│   │   ├── icon-144x144.png
│   │   ├── icon-152x152.png
│   │   ├── icon-192x192.png
│   │   ├── icon-384x384.png
│   │   └── icon-512x512.png
│   │   ├── badge-72x72.png     # Бейджи для уведомлений
│   │   ├── badge-96x96.png
│   │   └── shortcut-*.png      # Shortcut иконки
│   └── screenshots/            # Скриншоты для manifest (опционально)
│
├── templates/
│   ├── base.html               # Базовый шаблон с PWA поддержкой
│   ├── pwa.html                # Страница установки PWA
│   └── offline.html            # Страница офлайн-режима
│
└── main.py                     # Маршруты для PWA
```

## 🔧 Конфигурация

### manifest.json

Файл `manifest.json` содержит конфигурацию PWA:

```json
{
  "name": "FastPay Connect",
  "short_name": "FastPay",
  "description": "Интеграция платёжных систем через FastAPI",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#009688",
  "icons": [...],
  "shortcuts": [...],
  "share_target": {...}
}
```

### Service Worker

Service Worker (`service-worker.js`) реализует:

- **Cache First** стратегию для статических ресурсов
- **Network First** стратегию для HTML страниц
- **Network First с таймаутом** для API запросов
- Фоновую синхронизацию webhook-ов
- Push-уведомления

## 📲 Push-уведомления

### Включение уведомлений

1. Откройте `/pwa` страницу
2. Нажмите "Включить уведомления"
3. Разрешите уведомления в браузере

### Отправка уведомлений

```python
# Пример отправки push-уведомления
async def send_payment_notification(subscription, payment_data):
    import requests
    
    notification = {
        "title": "Новый платёж",
        "body": f"Платёж #{payment_data['id']} на сумму {payment_data['amount']}",
        "url": f"/payments/{payment_data['id']}",
        "icon": "/static/icons/icon-192x192.png",
    }
    
    # Отправка через VAPID (требуется настройка)
    requests.post(
        subscription.endpoint,
        json=notification,
        headers={...}
    )
```

### Подписка на push

```javascript
// JavaScript для подписки на push
async function subscribeToPush() {
    const registration = await navigator.serviceWorker.ready;
    
    const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: 'YOUR_VAPID_PUBLIC_KEY'
    });
    
    // Отправка подписки на сервер
    await fetch('/api/push/subscribe', {
        method: 'POST',
        body: JSON.stringify(subscription)
    });
}
```

## 📴 Офлайн режим

### Стратегии кэширования

| Тип ресурса | Стратегия | Описание |
|-------------|-----------|----------|
| Статика (CSS, JS, images) | Cache First | Сначала кэш, затем сеть |
| HTML страницы | Network First | Сначала сеть, затем кэш |
| API запросы | Network First + Timeout | Сеть с таймаутом 5с |

### Кэшируемые ресурсы

```javascript
const PRECACHE_ASSETS = [
  '/',
  '/offline',
  '/static/styles.css',
  '/static/manifest.json',
];
```

### Проверка кэша

Откройте DevTools → Application → Cache для просмотра закэшированных ресурсов.

## 🔧 Генерация иконок

### Автоматическая генерация

```bash
# Windows (PowerShell)
python scripts/generate_pwa_icons_simple.py

# Linux/macOS
python3 scripts/generate_pwa_icons_simple.py
```

### Ручная генерация

Используйте онлайн-генераторы:
- [PWA Icon Generator](https://www.pwaicon.com/)
- [RealFaviconGenerator](https://realfavicongenerator.net/)

### Требования к иконкам

- **Формат:** PNG
- **Размеры:** 72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512
- **Фон:** Прозрачный или сплошной цвет
- **Контент:** Логотип FastPay Connect

## 🧪 Тестирование PWA

### Chrome DevTools

1. Откройте DevTools (F12)
2. Перейдите в Application → Service Workers
3. Проверьте статус Service Worker

### Lighthouse

1. Откройте DevTools → Lighthouse
2. Выберите категорию "Progressive Web App"
3. Нажмите "Analyze page load"

### Проверка офлайн режима

1. Откройте DevTools → Network
2. Выберите "Offline" в dropdown
3. Обновите страницу

### Эмуляция устройства

1. Откройте DevTools → Toggle Device Toolbar (Ctrl+Shift+M)
2. Выберите устройство
3. Проверьте адаптивность

## 📊 Metrics & Monitoring

### Проверка статуса PWA

```javascript
// Проверка регистрации Service Worker
const registration = await navigator.serviceWorker.getRegistration();
console.log('SW registered:', registration);

// Проверка кэша
const cacheNames = await caches.keys();
console.log('Caches:', cacheNames);

// Проверка push подписки
const subscription = await registration.pushManager.getSubscription();
console.log('Push subscription:', subscription);
```

### API эндпоинты PWA

| Endpoint | Описание |
|----------|----------|
| `GET /manifest.json` | Manifest файл PWA |
| `GET /service-worker.js` | Service Worker скрипт |
| `GET /offline` | Страница офлайн-режима |
| `GET /pwa` | Страница установки PWA |

## 🔐 Безопасность

### HTTPS требование

PWA требует HTTPS соединения (кроме localhost).

### Content Security Policy

```python
# Добавление CSP заголовков
@app.middleware("http")
async def add_csp(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline'stackpath.bootstrapcdn.com fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com; "
        "img-src 'self' data: https:;"
    )
    return response
```

## 🐛 Troubleshooting

### Service Worker не регистрируется

**Проблема:** Service Worker не регистрируется

**Решение:**
1. Проверьте HTTPS (или localhost)
2. Очистите кэш браузера
3. Проверьте консоль на ошибки

### Push-уведомления не работают

**Проблема:** Уведомления не приходят

**Решение:**
1. Проверьте разрешения браузера
2. Убедитесь, что Service Worker активен
3. Проверьте VAPID ключи

### Приложение не устанавливается

**Проблема:** Кнопка установки не появляется

**Решение:**
1. Проверьте manifest.json на валидность
2. Убедитесь, что Service Worker активен
3. Проверьте HTTPS соединение

## 📚 Ресурсы

### Документация

- [MDN PWA Guide](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps)
- [Google PWA Checklist](https://web.dev/pwa-checklist/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web Push Protocol](https://tools.ietf.org/html/rfc8030)

### Инструменты

- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [Workbox](https://developers.google.com/web/tools/workbox)
- [PWA Builder](https://www.pwabuilder.com/)

## 📝 Changelog

### Версия 1.0.0 (Март 2026)

- ✅ Базовая PWA поддержка
- ✅ Service Worker с кэшированием
- ✅ manifest.json конфигурация
- ✅ Офлайн страница
- ✅ PWA установочная страница
- ✅ Push-уведомления (базовая поддержка)
- ✅ Иконки всех размеров
- ✅ Адаптивный дизайн

## 🤝 Вклад

Для добавления новых функций PWA:

1. Fork репозиторий
2. Создайте ветку (`git checkout -b feature/pwa-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add PWA feature'`)
4. Отправьте в fork (`git push origin feature/pwa-feature`)
5. Создайте Pull Request

## 📞 Контакты

**Автор:** Dupley Maxim Igorevich (QuadDarv1ne)

- 💻 GitHub: [QuadDarv1ne](https://github.com/QuadDarv1ne)
- 📬 Issues: [fastpay_connect/issues](https://github.com/QuadDarv1ne/fastpay_connect/issues)
- 📁 Репозиторий: [fastpay_connect](https://github.com/QuadDarv1ne/fastpay_connect)

---

<p align="center">
  <strong>FastPay Connect PWA - Платежи всегда под рукой</strong><br>
  <small>© 2026 Dupley Maxim Igorevich. Все права защищены.</small>
</p>
