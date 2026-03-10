/**
 * Cloudflare Worker для проксирования запросов к FastPay Connect API
 * 
 * Использование:
 * 1. wrangler login
 * 2. wrangler deploy
 * 
 * Документация: https://developers.cloudflare.com/workers/
 */

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    
    // API URL вашего приложения (замените на ваш production URL)
    const API_URL = env.API_URL || "https://fastpay-connect.example.com";
    
    // CORS preflight
    if (request.method === "OPTIONS") {
      return handleCORS(request);
    }
    
    // Health check endpoint
    if (url.pathname === "/health" || url.pathname === "/ready") {
      return handleHealthCheck(API_URL);
    }
    
    // Rate limiting с использованием Cloudflare
    const rateLimit = await checkRateLimit(request, env);
    if (!rateLimit.allowed) {
      return new Response(
        JSON.stringify({
          error: "Too Many Requests",
          message: "Превышен лимит запросов",
          retry_after: rateLimit.retryAfter,
        }),
        {
          status: 429,
          headers: {
            "Content-Type": "application/json",
            "Retry-After": rateLimit.retryAfter.toString(),
          },
        }
      );
    }
    
    // Проксирование запроса к backend
    try {
      const backendRequest = createBackendRequest(request, API_URL);
      const response = await fetch(backendRequest);
      
      // Кэширование ответов
      if (shouldCache(response, url)) {
        const cachedResponse = await cacheResponse(response, url);
        return cachedResponse;
      }
      
      return response;
    } catch (error) {
      return new Response(
        JSON.stringify({
          error: "Backend Error",
          message: "Ошибка подключения к серверу",
        }),
        {
          status: 503,
          headers: { "Content-Type": "application/json" },
        }
      );
    }
  },
};

/**
 * Обработка CORS preflight запросов
 */
function handleCORS(request: Request): Response {
  const headers = new Headers({
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGINS || "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Signature",
    "Access-Control-Max-Age": "86400",
  });
  
  return new Response(null, { headers });
}

/**
 * Проверка здоровья backend
 */
async function handleHealthCheck(apiUrl: string): Promise<Response> {
  try {
    const response = await fetch(`${apiUrl}/health`, { 
      method: "GET",
      cf: { cacheTtl: 60 }
    });
    return response;
  } catch {
    return new Response(
      JSON.stringify({ status: "unhealthy" }),
      { status: 503, headers: { "Content-Type": "application/json" } }
    );
  }
}

/**
 * Rate limiting с использованием Cloudflare Rate Limiting
 */
async function checkRateLimit(request: Request, env: Env): Promise<{
  allowed: boolean;
  retryAfter: number;
}> {
  // Использование Cloudflare Rate Limiting API
  const clientIP = request.headers.get("CF-Connecting-IP") || "unknown";
  const key = `rate_limit:${clientIP}`;
  
  // Проверка через KV Storage (если настроено)
  if (env.RATE_LIMIT_KV) {
    const count = await env.RATE_LIMIT_KV.get(key);
    const limit = env.RATE_LIMIT || 100; // 100 запросов в минуту
    const window = 60; // секунд
    
    if (count && parseInt(count) >= limit) {
      return { allowed: false, retryAfter: window };
    }
    
    await env.RATE_LIMIT_KV.put(key, (count ? parseInt(count) + 1 : 1).toString(), {
      expirationTtl: window,
    });
  }
  
  return { allowed: true, retryAfter: 0 };
}

/**
 * Создание запроса к backend
 */
function createBackendRequest(request: Request, apiUrl: string): Request {
  const url = new URL(request.url);
  const backendUrl = `${apiUrl}${url.pathname}${url.search}`;
  
  const headers = new Headers(request.headers);
  headers.delete("Host");
  headers.set("X-Forwarded-Host", url.host);
  headers.set("X-Forwarded-Proto", url.protocol.slice(0, -1));
  headers.set("X-Forwarded-For", request.headers.get("CF-Connecting-IP") || "");
  
  return new Request(backendUrl, {
    method: request.method,
    headers,
    body: request.body,
  });
}

/**
 * Проверка возможности кэширования
 */
function shouldCache(response: Response, url: URL): boolean {
  // Кэшируем только GET запросы и успешные ответы
  if (response.method !== "GET" || response.status !== 200) {
    return false;
  }
  
  // Не кэшируем API endpoints
  const noCachePaths = ["/payments", "/webhooks", "/admin"];
  return !noCachePaths.some(path => url.pathname.startsWith(path));
}

/**
 * Кэширование ответа
 */
async function cacheResponse(response: Response, url: URL): Promise<Response> {
  const cache = caches.default;
  const cacheKey = new Request(url.toString(), response);
  
  // Клонируем ответ для кэширования
  const responseToCache = response.clone();
  
  // Устанавливаем TTL для кэша
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "public, max-age=300"); // 5 минут
  
  const cachedResponse = new Response(responseToCache.body, {
    status: responseToCache.status,
    statusText: responseToCache.statusText,
    headers,
  });
  
  // Сохраняем в кэш (асинхронно, не ждём завершения)
  ctx.waitUntil(cache.put(cacheKey, cachedResponse.clone()));
  
  return response;
}
