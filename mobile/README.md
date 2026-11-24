# АЛЬБИОН — Мобильный PWA

Мобильное веб-приложение для просмотра фотографий фотобазы АЛЬБИОН.

## Структура проекта

```
mobile/
├── index.html          # Главная страница
├── manifest.json       # PWA манифест
├── sw.js               # Service Worker (offline-кэш)
├── css/
│   └── main.css        # Основные стили
├── js/
│   ├── api.js          # API-клиент (FastAPI endpoints)
│   ├── auth.js         # Аутентификация (JWT/session tokens)
│   └── main.js         # Основная логика приложения
└── assets/
    └── icons/
        ├── icon-192.png
        └── icon-512.png
```

## Статус

| Этап | Статус |
|---|---|
| 1. Каркас (HTML/CSS/JS, API client, auth) | ✅ Завершён |
| 2. Грид фото (API integration, lazy loading, pagination) | ✅ Завершён |
| 3. Footer (address picker, period selector) | ✅ Завершён |
| 4. Избранное (sync with desktop) | ✅ Завершён |
| 5. Меню (groups, settings) | ✅ Завершён |
| 6. PWA (offline, optimization) | ⚠️ Частично: SW, кэш превью, автообновление и Lighthouse (PWA/Perf/A11y/BP — 100) есть; офлайн-очереди изменений нет |

Реальные превью (`/api/v1/photos/{id}/previews/{size}`) подключены для плиток
фото, карточки и плиток дат; адресные плитки намеренно текстовые. Подробности
и актуальные ограничения — в `docs/mobile_pwa_backend_integration.md`; ранний
`docs/mobile_pwa_complete_report.md` обновлён и больше не описывает превью как
CSS-заглушки.

## Запуск

Мобильный PWA — отдельная статическая страница, обращающаяся к тому же FastAPI backend, что и десктопный Quasar SPA.

### Основной способ (порт 8010)

1. Бэкенд запущен (`scene-api`, `SCENE_API_PORT=8010`).
2. Откройте PWA:

```
http://<host>:8010/mobile/               # в локальной сети
https://albion-base.cloudpub.ru/mobile/  # снаружи (TLS-туннель)
```

3. Войдите логином и паролем из базы PhotoBAse (`public.users`) — те же, что
   на десктопе. Гость: `гость` / `альбион`, если аккаунт есть в базе.

**Установка на телефон (PWA):** адрес открыт по HTTPS, поэтому приложение
ставится: Android Chrome — меню ⋮ → «Установить приложение»; iOS Safari —
«Поделиться» → «На экран “Домой”».

### Отдельный dev-сервер (опционально)

```bash
cd /home/alexice/projects/albion-photobase/mobile
python3 -m http.server 8080
# API-база определится как http://<host>:8010/api/v1
```

Для кросс-origin режима добавьте `http://<host>:8080` в `SCENE_CORS_ORIGINS`
(в `/home/alexice/.config/scene-fingerprint.env`) и перезапустите `scene-api`.
В этом режиме куки не передаются между портами — вход работает по
`Authorization`-заголовку, а превью в `<img>` могут требовать прямого
same-origin (рекомендуется /mobile/ на бэкенде).

### Production

Nginx не обязателен для самой статики (её отдаёт FastAPI). Прокси нужен только
если вы выносите TLS-терминацию:

```nginx
server {
    listen 443 ssl;
    server_name photos.example.com;

    location / {
        proxy_pass http://127.0.0.1:8010;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

PWA-установка («Добавить на главный экран») требует HTTPS или localhost.

### Authentication

**Credentials берутся из:**
- База данных: `public.users` (таблица PhotoBAse)
- Таблица: `users` с колонками `name`, `password_hash` (scrypt)
- Те же credentials, что и в десктопном приложении / веб-интерфейсе

**API endpoint:**
- `POST /api/v1/auth/login` — body: `{ “name”: “username”, “password”: “password” }`
- Возвращает: `{ “token”: “session_token”, “user”: { “name”: “...”, “role”: “...” } }`

**Роли (scopes):**
- **Администратор**: `{“*”}` (все права)
- **Менеджер**: `read, collections:write, searches:write, upload:write, jobs:read/write`
- **Гость**: `{“read”}` (только просмотр)

## Функционал

### Закладки

- **📅 По датам** — альбомы по датам съёмки (Сегодня, Вчера, 15 ноября 2021, ...)
- **📁 По адресам** — подборки адресов (синхронизация с десктопом) + отдельные адреса

### Функции

- 🔍 Поиск по адресам, клиентам, брендам
- 📍 Выбор адресов (mulit-select через bottom sheet)
- ❤️ Избранное (синхронизация с десктопом)
- 📤 Экспорт через Web Share API
- 🌙 Тёмная тема
- 🔄 Синхронизация подборок с десктопом
- ➕ Создание новых подборок
-  Offline-кэш (API + превью)

### API Endpoints

Используется тот же API, что и десктопная версия:

| Действие | Endpoint | Метод |
|---|---|---|
| Логин | `/api/v1/auth/login` | POST |
| Текущий пользователь | `/api/v1/auth/me` | GET |
| Фото (пагинация) | `/api/v1/photos?cursor=...&limit=...` | GET |
| Превью фото | `/api/v1/photos/{id}/previews/{size}` | GET |
| Подборки | `/api/v1/collections?kind=favorites` | GET |
| Избранное | `/api/v1/favorites` | POST/DELETE |
| Синхронизация | `/api/v1/jobs/ingest` | POST |
| Экспорт | `/api/v1/media-links` | POST |

## PWA Features

- **Manifest**: `manifest.json` с иконками 192x192 и 512x512
- **Service Worker**: `sw.js` с network-first стратегией для API, cache-first для статики
- **Offline**: кэширование API-ответов и превью (IndexedDB + Cache API)
- **Auto-cleanup**: удаление старых кэш-записей (> 7 дней)

## Tech Stack

- **HTML5** + **CSS3** (без фреймворков)
- **Vanilla JavaScript** (ES6+)
- **FastAPI** бэкенд (тот же, что и десктоп)
- **PostgreSQL** (та же БД, что и десктоп)

## Размер

- `index.html`: ~5 КБ
- `css/main.css`: ~15 КБ
- `js/api.js`: ~3 КБ
- `js/auth.js`: ~2 КБ
- `js/main.js`: ~15 КБ
- **Итого**: ~40 КБ (без изображений)

## Документация

| Документ | Содержание |
|---|---|
| `docs/mobile_pwa_complete_report.md` | Финальный отчёт: реализовано, запуск, production |
| `docs/mobile_pwa_plan.md` | План работ и визуалы |
| `docs/mobile_pwa_production_setup.md` | Production setup guide |
| `docs/mobile_pwa_backend_integration.md` | Интеграция с реальным бэкендом |
| `docs/mobile_pwa_lighthouse.md` | Lighthouse-аудит и оставшиеся замечания |
| `docs/mobile_pwa_phase2_report.md` | Отчёт по Этапу 2: Грид фото |
| `docs/mobile_pwa_login_fix.md` | Fix: login не работал |
| `docs/mobile_pwa_correction_summary.md` | Исправления по результатам ревью |

## License

Copyright © 2026 АЛЬБИОН. Все права защищены.
