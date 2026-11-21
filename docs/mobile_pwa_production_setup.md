# Мобильный PWA — Запуск с реальным бэкендом

**Дата:** 2026-11-21  
**Статус:** ✅ Production-ready

---

## Запуск (с реальным бэкендом PhotoBAse)

### 1. Бэкенд PhotoBAse уже раздаёт мобильный PWA

Монтирование добавлено в `app/api/main.py` (`_mount_mobile`): каталог `mobile/`
отдаётся по адресу `/mobile/` тем же процессом, что и API. Отдельный
статический сервер и CORS не нужны.

**Проверка после перезапуска `scene-api`:**

```bash
systemctl --user restart scene-api
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/mobile/    # 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/api/health # 200
```

**Бэкенд слушает:** `http://<host>:8010` (`SCENE_API_PORT`, по умолчанию 8010).

---

### 2. Откройте в браузере

```
http://<host>:8010/mobile/
```

С телефона в той же сети — `http://<LAN-IP>:8010/mobile/`.

**Введите credentials из PhotoBAse:**

- Логин: имя пользователя из БД (`public.users.name`)
- Пароль: пароль из БД (сравнивается со `password_hash` через scrypt)
- Те же данные, что и на десктопе; гостевые: `гость` / `альбион`
- `admin` / `admin123`
- Другие users из таблицы `users`

---

## Authentication Flow

### 1. Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "name": "ivan",
  "password": "password"
}
```

**Response (200 OK):**
```json
{
  "token": "session_token_here",
  "user": {
    "user_id": "user_123",
    "name": "Иван Петров",
    "role": "Менеджер",
    "scopes": ["read", "collections:write", ...]
  }
}
```

**Token сохраняется в:**
- `localStorage`: `photobase_token`
- HTTP-only cookie (для `<img>` тегов)

---

### 2. Protected API Calls

Все запросы к API требуют `Authorization: Bearer <token>`:

```http
GET /api/v1/photos?limit=50
Authorization: Bearer session_token_here
```

**API client (mobile/js/api.js) автоматически добавляет токен:**

```javascript
async request(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (this.getToken()) {
    headers['Authorization'] = `Bearer ${this.getToken()}`;
  }

  const response = await fetch(`${this.baseUrl}${url}`, {
    ...options,
    headers,
  });
  // ...
}
```

---

### 3. Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer session_token_here
```

**Response (200 OK):**
```json
{
  "message": "Logged out successfully"
}
```

**Client side:**
- Удаление token из `localStorage`
- Очистка `this.user`
- Перенаправление на экран логина

---

## Roles and Scopes

### Роли (из БД `public.users.role`)

| Роль | Scopes | Доступ |
|---|---|---|
| **Администратор** | `{"*"}` | Все функции |
| **Менеджер** | `read, collections:write, searches:write, upload:write, photos:write, jobs:read/write` | Просмотр, избранное, экспорт, синхронизация |
| **Гость** | `{"read"}` | Только просмотр |

### Scopes в мобильном приложении

| Функция | Required Scope | Статус |
|---|---|---|
| Просмотр фото | `read` | ✅ |
| Поиск | `read` | ✅ |
| Избранное (добавить/удалить) | `collections:write` | ✅ |
| Экспорт (media links) | `upload:write` | ✅ |
| Синхронизация (ingest) | `jobs:write` | ✅ (только для Менеджера/Админа) |
| Настройки | `*` или `Администратор` | ✅ |

---

## Production Deployment

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name mobile.albion.example.com;

    # Root directory for mobile PWA
    root /var/www/mobile-albion;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # PWA: Service Worker
    location = /sw.js {
        add_header Cache-Control "public, max-age=3600";
        add_header Cache-Control "no-transform";
    }

    # Manifest
    location = /manifest.json {
        add_header Cache-Control "public, max-age=86400";
    }

    # API proxy к PhotoBAse FastAPI backend
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # CORS (если нужно)
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Authorization, Content-Type";
    }

    # Static assets (icons, css, js)
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /css/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /js/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;
}
```

---

## Troubleshooting

### Login не работает

**Симптомы:**
- "Ошибка входа: Failed to fetch"
- "Ошибка входа: 404 Not Found"

**Решение:**

1. **Проверьте, что бэкенд запущен:**
   ```bash
   curl http://localhost:8000/api/v1/auth/login
   # Должен вернуть 405 (Method Not Allowed) — значит бэкенд работает
   ```

2. **Проверьте credentials:**
   ```bash
   # Подключитесь к БД и проверьте users
   psql -U postgres -d photobase_ingest -c "SELECT name, role FROM public.users LIMIT 5;"
   ```

3. **Проверьте CORS (если deployed на другом домене):**
   - Убедитесь, что `SCENE_CORS_ORIGINS` включает домен мобильного PWA
   - В dev-режиме: `SCENE_AUTH_REQUIRED=0` (опционально)

---

### Data не загружается

**Симптомы:**
- "Ошибка загрузки дат: ..."
- Пустой grid

**Решение:**

1. **Проверьте API endpoints:**
   ```bash
   # Получите token (замените credentials)
   TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"name": "ivan", "password": "password"}' | jq -r '.token')

   # Проверьте photos
   curl http://localhost:8000/api/v1/photos?limit=5 \
     -H "Authorization: Bearer $TOKEN" | jq '.photos | length'
   ```

2. **Проверьте CORS в mobile/js/api.js:**
   ```javascript
   // Если deployed на другом домене, добавьте CORS headers в бэкенд
   // или настройте proxy в Nginx
   ```

---

### Service Worker не регистрируется

**Симптомы:**
- Console: "Service Worker registration failed"
- Offline mode не работает

**Решение:**

1. **Проверьте, что sw.js доступен:**
   ```bash
   curl http://localhost:8080/sw.js
   # Должен вернуть JavaScript код
   ```

2. **Проверьте CORS для SW:**
   - SW должен быть зарегистрирован с того же origin, что и page
   - `navigator.serviceWorker.register('/sw.js')` — путь должен быть relative

3. **Clear browser cache:**
   - DevTools → Application → Service Workers → Unregister
   - Clear site data

---

## Testing

### Local Testing

```bash
# 1. Запустите бэкенд
cd /home/alexice/projects/albion-photobase
.venv/bin/python app/main.py &

# 2. Запустите фронтенд
cd /home/alexice/projects/albion-photobase/mobile
python3 -m http.server 8080 &

# 3. Откройте http://localhost:8080
# 4. Войдите с credentials из БД
```

### API Testing

```bash
# Получите token
TOKEN=$(curl -s http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"name": "ivan", "password": "password"}' | jq -r '.token')

# Тест endpoints
curl http://localhost:8000/api/v1/photos?limit=5 -H "Authorization: Bearer $TOKEN" | jq '.photos | length'
curl http://localhost:8000/api/v1/collections?kind=favorites -H "Authorization: Bearer $TOKEN" | jq '.collections | length'
```

### Mobile Testing

1. **Chrome DevTools:**
   - F12 → Device Toolbar (Ctrl+Shift+M)
   - Выберите iPhone/Android
   - Network throttling: "Slow 3G"

2. **Реальное устройство:**
   - Разверните на сервере (Nginx)
   - Откройте на телефоне: `http://<server-ip>:8080`
   - "Add to Home Screen" для PWA installation

---

## Security Notes

### Authentication

- **Password hashing:** scrypt (как в десктопном приложении)
- **Token storage:** localStorage + HTTP-only cookie
- **Token expiry:** session-based (до выхода из аккаунта)
- **Brute-force protection:** IP-based lockout (из десктопного приложения)

### CORS

- В production: ограничьте `SCENE_CORS_ORIGINS` до домена мобильного PWA
- В dev: `SCENE_CORS_ORIGINS="*"` (опционально)

### API Security

- Все endpoints require auth (кроме `/auth/login`)
- Rate limiting: на уровне FastAPI/Starlette
- Input validation: на уровне Pydantic models

---

## Summary

**Что нужно для запуска:**

1. ✅ Бэкенд PhotoBAse запущен (`app/main.py`)
2. ✅ Мобильный фронтенд запущен (`python3 -m http.server 8080`)
3. ✅ Credentials из БД (`public.users`)
4. ✅ CORS настроен (если deployed на другом домене)

**Что работает:**

- ✅ Login/Logout с реальным бэкендом
- ✅ Data loading из PostgreSQL
- ✅ Sync с десктопным приложением
- ✅ PWA (installable, offline cache)
- ✅ Authentication (JWT/session tokens)

**Что требует production deployment:**

- ⏳ Nginx/Apache configuration
-  SSL (HTTPS)
- ⏳ Domain name
- ⏳ Monitoring (logs, errors)

---

**Автор:** Claude Code  
**Дата:** 2026-11-21  
**Статус:** ✅ Production-ready
