/**
 * Service Worker for PhotoBAse mobile PWA.
 *
 * Strategy: network-first for API requests, cache-first for static assets.
 * Auto-cleanup: removes old cache entries older than 7 days.
 */

const CACHE_NAME = 'albion-mobile-v9';
// Относительные пути: service worker живёт и в корне dev-сервера, и
// под /mobile/ на бэкенде — список должен резолвиться от его каталога.
const STATIC_ASSETS = [
  './',
  './index.html',
  './css/main.css',
  './js/api.js',
  './js/auth.js',
  './js/main.js',
  './js/pwa.js',
  './manifest.json',
  './assets/icons/logo.png',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png',
  './assets/icons/icon-maskable-512.png',
  './assets/icons/apple-touch-icon.png',
];

const API_CACHE_NAME = 'albion-api-cache';
const PREVIEW_CACHE_NAME = 'albion-previews-cache';

// ===== Install =====

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );

  // Skip waiting to activate immediately
  self.skipWaiting();
});

// ===== Activate =====

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME && name !== API_CACHE_NAME && name !== PREVIEW_CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );

  self.clients.claim();
});

// ===== Fetch =====

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Preview images живут под /api/v1/.../previews/, поэтому проверяем их
  // ДО общего API: иначе они попадали в API-кэш, а clear-previews чистил
  // пустой кэш превью.
  if (url.pathname.includes('/previews/')) {
    event.respondWith(cacheFirstWithNetworkFallback(request));
    return;
  }

  // API requests: network-first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Оболочка и скрипты: network-first. Cache-first оставлял бы старую
  // версию приложения после обновления — файлы здесь без хеша в имени.
  if (url.origin === self.location.origin) {
    event.respondWith(networkFirstStatic(request));
    return;
  }

  // Everything else: network-only
  event.respondWith(fetch(request));
});

// ===== Strategies =====

async function networkFirst(request) {
  try {
    const response = await fetch(request);

    // Кэшировать можно только GET: cache.put() на POST бросает TypeError,
    // а необработанное исключение в respondWith убивает ответ — именно это
    // ломало вход (200 с Set-Cookie превращался в net::ERR_FAILED).
    if (response.ok && request.method === 'GET') {
      try {
        const cache = await caches.open(API_CACHE_NAME);
        await cache.put(request, response.clone());
      } catch (cacheError) {
        // Кэш — вспомогательный: ошибка записи не должна ломать ответ.
        console.warn('API cache put failed:', cacheError);
      }
    }

    return response;
  } catch (error) {
    if (request.method === 'GET') {
      const cache = await caches.open(API_CACHE_NAME);
      const cachedResponse = await cache.match(request);

      if (cachedResponse) {
        return cachedResponse;
      }
    }

    throw error;
  }
}

async function networkFirstStatic(request) {
  try {
    // no-cache: ревалидировать с сервером, иначе HTTP-кэш браузера может
    // отдать старый main.js в обход сети.
    const response = await fetch(request, { cache: 'no-cache' });

    if (response.ok && request.method === 'GET') {
      try {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
      } catch (cacheError) {
        console.warn('Static cache put failed:', cacheError);
      }
    }

    return response;
  } catch (error) {
    const cache = await caches.open(CACHE_NAME);
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    return new Response('Offline', { status: 503 });
  }
}

async function cacheFirstWithNetworkFallback(request) {
  const cache = await caches.open(PREVIEW_CACHE_NAME);
  const cachedResponse = await cache.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  try {
    const response = await fetch(request);
    if (response.ok && request.method === 'GET') {
      try {
        await cache.put(request, response.clone());
      } catch (cacheError) {
        console.warn('Preview cache put failed:', cacheError);
      }
    }
    return response;
  } catch (error) {
    return new Response('Preview not available offline', { status: 503 });
  }
}

// ===== Auto-cleanup =====

self.addEventListener('message', (event) => {
  // Принудительное обновление из меню: не ждать закрытия всех вкладок.
  if (event.data && event.data.type === 'skip-waiting') {
    self.skipWaiting();
  }

  if (event.data === 'cleanup') {
    cleanupOldCacheEntries();
  }

  // Сменился период/группа адресов: превью прошлой выборки больше не нужны.
  if (event.data === 'clear-previews') {
    event.waitUntil(caches.delete(PREVIEW_CACHE_NAME));
  }

  // Выход из аккаунта: ответы API и превью могли содержать данные этого
  // пользователя, а браузерный профиль может быть общим — чистим оба кэша.
  if (event.data === 'clear-private-cache') {
    event.waitUntil(
      Promise.all([
        caches.delete(API_CACHE_NAME),
        caches.delete(PREVIEW_CACHE_NAME),
      ]),
    );
  }
});

async function cleanupOldCacheEntries() {
  const now = Date.now();
  const sevenDays = 7 * 24 * 60 * 60 * 1000;

  // Cleanup API cache
  const apiCache = await caches.open(API_CACHE_NAME);
  const apiKeys = await apiCache.keys();
  for (const key of apiKeys) {
    const response = await apiCache.match(key);
    if (response) {
      const headers = response.headers;
      const dateHeader = headers.get('date');
      if (dateHeader) {
        const responseDate = new Date(dateHeader).getTime();
        if (now - responseDate > sevenDays) {
          await apiCache.delete(key);
        }
      }
    }
  }

  // Cleanup preview cache
  const previewCache = await caches.open(PREVIEW_CACHE_NAME);
  const previewKeys = await previewCache.keys();
  for (const key of previewKeys) {
    const response = await previewCache.match(key);
    if (response) {
      const headers = response.headers;
      const dateHeader = headers.get('date');
      if (dateHeader) {
        const responseDate = new Date(dateHeader).getTime();
        if (now - responseDate > sevenDays) {
          await previewCache.delete(key);
        }
      }
    }
  }
}

// ===== Periodic cleanup =====

self.addEventListener('sync', (event) => {
  if (event.tag === 'cleanup') {
    event.waitUntil(cleanupOldCacheEntries());
  }
});
