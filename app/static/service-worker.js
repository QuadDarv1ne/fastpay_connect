/**
 * Service Worker для FastPay Connect PWA
 * Версия: 1.0.0
 * Автор: Dupley Maxim Igorevich
 * 
 * Функционал:
 * - Кэширование статических ресурсов
 * - Офлайн-режим
 * - Фоновая синхронизация
 * - Push-уведомления
 */

const CACHE_NAME = 'fastpay-connect-v1';
const STATIC_CACHE = 'fastpay-static-v1';
const DYNAMIC_CACHE = 'fastpay-dynamic-v1';
const OFFLINE_PAGE = '/offline';

// Ресурсы для предварительного кэширования
const PRECACHE_ASSETS = [
  '/',
  '/offline',
  '/static/styles.css',
  '/static/manifest.json',
];

// Ресурсы, которые не нужно кэшировать
const NON_CACHED_REQUESTS = [
  'analytics',
  'tracking',
  'telemetry',
];

// Установка Service Worker
self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('[SW] Precaching static assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => {
        console.log('[SW] Installation complete, skipping waiting');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[SW] Precaching failed:', error);
      })
  );
});

// Активация Service Worker
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((cacheName) => {
              // Удаляем старые кэши
              return cacheName.startsWith('fastpay-') && 
                     cacheName !== STATIC_CACHE && 
                     cacheName !== DYNAMIC_CACHE;
            })
            .map((cacheName) => {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            })
        );
      })
      .then(() => {
        console.log('[SW] Activation complete, claiming clients');
        return self.clients.claim();
      })
  );
});

// Перехват запросов (Network First с fallback в кэш)
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Игнорируем некэшируемые запросы
  if (NON_CACHED_REQUESTS.some(keyword => url.pathname.includes(keyword))) {
    return;
  }
  
  // Игнорируем запросы не к нашему домену
  if (url.origin !== location.origin) {
    return;
  }
  
  // Обработка запросов
  if (request.method !== 'GET') {
    return;
  }
  
  // Статические ресурсы - Cache First
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }
  
  // HTML страницы - Network First с fallback
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirst(request));
    return;
  }
  
  // API запросы - Network First с таймаутом
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithTimeout(request));
    return;
  }
  
  // Остальные запросы - Cache First
  event.respondWith(cacheFirst(request));
});

/**
 * Стратегия Cache First
 * Сначала проверяем кэш, затем сеть
 */
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  
  if (cachedResponse) {
    return cachedResponse;
  }
  
  try {
    const networkResponse = await fetch(request);
    
    // Кэшируем успешные ответы
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache-first failed:', error);
    
    // Для навигационных запросов возвращаем офлайн-страницу
    if (request.headers.get('accept')?.includes('text/html')) {
      return caches.match(OFFLINE_PAGE);
    }
    
    throw error;
  }
}

/**
 * Стратегия Network First
 * Сначала сеть, при неудаче - кэш
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    // Кэшируем успешные ответы
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', error);
    
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Для навигационных запросов возвращаем офлайн-страницу
    if (request.headers.get('accept')?.includes('text/html')) {
      return caches.match(OFFLINE_PAGE);
    }
    
    throw error;
  }
}

/**
 * Network First с таймаутом для API
 */
async function networkFirstWithTimeout(request, timeout = 5000) {
  const timeoutPromise = new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Timeout')), timeout);
  });
  
  try {
    const networkResponse = await Promise.race([fetch(request), timeoutPromise]);
    
    if (networkResponse.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] API network failed, trying cache:', error);
    
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Возвращаем ошибку для API
    return new Response(
      JSON.stringify({ error: 'offline', message: 'No connection' }),
      { 
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}

/**
 * Проверка, является ли ресурс статическим
 */
function isStaticAsset(pathname) {
  const staticExtensions = [
    '.css', '.js', '.json', '.png', '.jpg', '.jpeg', 
    '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot'
  ];
  
  return staticExtensions.some(ext => pathname.endsWith(ext)) ||
         pathname.startsWith('/static/');
}

// Фоновая синхронизация
self.addEventListener('sync', (event) => {
  console.log('[SW] Sync event:', event.tag);
  
  if (event.tag === 'sync-webhooks') {
    event.waitUntil(syncWebhooks());
  }
});

/**
 * Синхронизация webhook-ов в фоновом режиме
 */
async function syncWebhooks() {
  console.log('[SW] Syncing webhooks...');
  
  try {
    // Получаем отложенные webhook-и из IndexedDB
    const pendingWebhooks = await getPendingWebhooks();
    
    for (const webhook of pendingWebhooks) {
      try {
        await fetch('/api/monitoring/webhooks/sync', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(webhook),
        });
        
        // Удаляем успешный webhook из очереди
        await removePendingWebhook(webhook.id);
      } catch (error) {
        console.error('[SW] Failed to sync webhook:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Webhook sync failed:', error);
  }
}

// Push-уведомления
self.addEventListener('push', (event) => {
  console.log('[SW] Push received');
  
  let data = {};
  
  try {
    data = event.data?.json() || {};
  } catch (error) {
    data = { title: 'FastPay Connect', body: 'Новое уведомление' };
  }
  
  const options = {
    body: data.body || 'Новое событие в FastPay Connect',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: data.primaryKey || 1,
      url: data.url || '/',
    },
    actions: [
      { action: 'view', title: 'Просмотр' },
      { action: 'dismiss', title: 'Закрыть' },
    ],
    tag: data.tag || 'payment-notification',
    renotify: true,
  };
  
  event.waitUntil(
    self.registration.showNotification(data.title || 'FastPay Connect', options)
  );
});

// Обработка кликов по уведомлениям
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action);
  
  event.notification.close();
  
  if (event.action === 'dismiss') {
    return;
  }
  
  const urlToOpen = event.notification.data?.url || '/';
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((windowClients) => {
        // Проверяем, есть ли уже открытая вкладка
        for (const client of windowClients) {
          if (client.url === urlToOpen && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Открываем новую вкладку
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

// Сообщения от клиента
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});

/**
 * Получить отложенные webhook-и из IndexedDB
 */
async function getPendingWebhooks() {
  // Заглушка для будущей реализации IndexedDB
  return [];
}

/**
 * Удалить webhook из очереди
 */
async function removePendingWebhook(id) {
  // Заглушка для будущей реализации IndexedDB
}

console.log('[SW] Service Worker loaded');
