# Мобильный PWA — Исправления по результатам ревью

**Дата:** 2026-11-21  
**Основание:** Ревью плана и макетов агентом + сверка с реальным API

---

## Что было исправлено

### 1. Tech stack

| Было | Стало |
|---|---|
| Vanilla JS + CSS Grid | **Quasar v2** (Vite + Quasar plugin) |

**Почему:** Quasar v2 уже используется в десктопе, имеет встроенную PWA-поддержку (`@quasar/pwa-*`), drawer-компоненты, responsive-утилиты, service worker generation. Переиспользуем те же API-клиенты и компоненты.

---

### 2. API endpoints (все пути corrected)

| Было | Стало |
|---|---|
| `/v1/photos` | `/api/v1/photos` |
| `/v1/photos/<id>/preview` | `/api/v1/photos/<id>/previews/{size}` (size: `small`/`middle`) |
| `/v1/photos?search=...` | `/api/v1/photos?q=...&brand=...&tag=...&category=...` |
| `/v1/favorites?user_id=...` | `/api/v1/collections?kind=favorites` → `/api/v1/collections/{id}/members` |
| `/auth/login` | `/api/v1/auth/login` (POST: `{name, password}`) |
| `/auth/me` | `/api/v1/auth/me` |

**Добавлено:**
- `/api/v1/search/suggestions?q=...` — autocomplete для мобильного поиска
- `/api/v1/media-links` — экспорт в Albion cloud (scope `upload:write`)

---

### 3. Pagination

| Было | Стало |
|---|---|
| `limit=...` (offset-based) | **Cursor-based** (`cursor` + `next_cursor`) |

**Почему:** Реальный API использует base64 cursor pagination. Мобильный UI должен передавать `next_cursor` при бесконечном скролле.

---

### 4. Favorites data model

| Было | Стало |
|---|---|
| `user_favorites` table (не существует) | `collections` + `collection_members` tables |

**Как работает:** Избранное = collection с `scope='photos'`, `kind='Моя'`. Синхронизация через `/api/v1/collections` и `/api/v1/collections/{id}/members`.

---

### 5. Auth flow

| Было | Стало |
|---|---|
| JWT + refresh token | **Session token** в localStorage (ключ `photobase_token`) |

**Почему:** В проекте нет JWT refresh token. Токен хранится до выхода из аккаунта. HTTP-заголовки: `Authorization: Bearer <token>`.

---

### 6. Group tabs (добавлено)

**5 табов адресов:** screens, rostov, cities, roads, small  
**Как отображать:** горизонтальная прокрутка под шапкой  
**API:** `?group=` query parameter

---

### 7. Export mechanism

| Было | Стало |
|---|---|
| Web Share API напрямую | **`POST /api/v1/media-links`** → Albion cloud → shareable links |

**Почему:** Для экспорта нужен scope `upload:write` и генерация ссылок через Albion. Web Share API используется для отправки готовых ссылок в мессенджеры.

---

## Обновлённые файлы

| Файл | Изменения |
|---|---|
| `docs/mobile_pwa_plan.md` | Tech stack, API endpoints, pagination, favorites model, auth, risks |
| `docs/mobile_pwa_wireframes.html` | API table, key decisions, risks |

---

## Что осталось согласовать

1. **Группы адресов в мобильном UI:** горизонтальная прокрутка под шапкой или через бургер-меню?
2. **Размер превью по умолчанию:** SMALL (640px) для экономии трафика или MIDDLE (1280px)?
3. **Офлайн-кэш:** только API-запросы или и превью тоже?

---

**Статус:** План готов к реализации после согласования оставшихся вопросов.
