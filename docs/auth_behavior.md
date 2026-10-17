# Алгоритм авторизации и сохранения настроек

Дата: 2026-10-17

## 1. Принципы

1. **Сервер — единственный источник правды.** Каждая ручка проверяет scope;
   UI только прячет недоступное, но не заменяет проверку.
2. **Fail-closed.** Нет учётных данных → 401; нет нужного scope → 403;
   неизвестная роль → права `read` (как у Гостя).
3. Настройки интерфейса принадлежат **пользователю**, а не браузеру; у Гостя
   они не сохраняются вовсе.

## 2. Роли и scopes (`app/api/auth.py::ROLE_SCOPES`)

| Роль | Scopes |
|---|---|
| Администратор | `*` |
| Менеджер | `read`, `collections:write`, `searches:write`, `upload:write`, `photos:write`, `jobs:read`, `jobs:write`, `addresses:write`, `videos:read`, `videos:write`, `videos:download`, `originals` |
| Гость | `read` |

`users:manage` и `settings:write` — только Администратор.

## 3. Алгоритм входа и отрисовки

```
SPA старт
  → session.load(): GET /v1/auth/me                          (публичная)
  → user = {user_id, name, role}, auth_enabled
  → если auth_enabled и user = null → экран входа
  → иначе afterAuth():
       canPersist = !auth_enabled || role !== 'Гость'
       display.setPersistence(canPersist)
       если !canPersist: display.reset()                    (заводские настройки)
       photos.loadSelectionState({persist: canPersist})
       если canPersist: display.loadFromServer()            (GET /v1/selection)
       booted = true → рендер интерфейса
```

Маршрутизатор (`frontend/src/router/index.js`):

```
переход на /technical
  → роль ∈ {Администратор, Менеджер} ? маршрут : redirect '/'
```

Серверных ручек технического раздела нет в публичном API: пользователи
(`users:manage`), настройки QWEN (`settings:write`) закрыты scope-проверкой.

## 4. Гость: что видно и что запрещено

| Возможность | UI | Сервер |
|---|---|---|
| Адреса, грид, клиенты | видит | `read` |
| Фильтры, текстовая строка поиска | доступны | `read` |
| Переключение Фотогалерея/Видео | доступно | `read` |
| Поиск по загруженному фото/видео | **скрыт** (камера, «Авто», окно ручного поиска) | `searches:write` → 403 |
| Технический раздел | шестерёнка скрыта, `/technical` редиректит | админ-ручки за scope |
| Скачивание фото/видео/архива, «Оригинал», «Сохранить» | **скрыты** (кнопки, контекстное меню, карточка) | `originals`, `videos:download` → 403 |
| Окно редактирования карточки (адрес, текст, пересканирование) | **скрыто** | `addresses:write`, `photos:write`, `jobs:write` → 403 |
| Подборки (создание/сохранение, «В подборку») | **скрыты** | `collections:write` → 403 |
| Сохранение настроек | отключено | `PUT /v1/selection` → 403 |

Ключевые точки UI:

- `PhotosGrid.vue`: `canUseCollective` (Администратор/Менеджер) гейтит
  скачивание, подборки, «Оригинал/Сохранить», редактирование адреса;
  `canSearchMedia` — камеру и ручной поиск; `canRunQwen` — пересканирование.
- `VideosGrid.vue`: `isStaff` гейтит воспроизведение, сжатие и скачивание.
- `App.vue`: `canUseTech` гейтит шестерёнку; `afterAuth()` управляет
  сохранением.
- `router/index.js`: guard `/technical`.

## 5. Алгоритм сохранения настроек

| Состояние | Кто | Куда |
|---|---|---|
| Раскладка, панели, поля списка, режим имён скачивания | staff | `localStorage` + `PUT /v1/selection {display}` (debounce 800 мс) |
| Базовая раскладка («Вернуть базовые», файл) | staff | `localStorage` + `PUT /v1/selection {display_base}` |
| Отметки фото/адресов/клиентов | — | **не сохраняются между сессиями** (владелец, 2026-10-17): при входе грид показывает все фото, выделения адресов/клиентов пусты |
| Гость | — | **ничего не сохраняется**: ни localStorage, ни сервер; при каждом входе заводские значения |

Сервер хранит состояние в `manager_selections.state` (schema/015); ключ
`selected`/`display`/`display_base` сливается, а не перезаписывается целиком.

## 6. Проверки

- `tests/test_role_scopes.py` — политика ролей и 401/403 без БД.
- `tests/test_video_api.py` — у Гостя нет видео-scopes и `originals`.
- `tests/test_api_collections.py` — Гость не получает `collections:write`.
- `frontend/tests/app-shell.spec.js` — сценарий Гостя: грид и текстовая строка
  доступны, камера/скачивание/подборки/техраздел отсутствуют в DOM.
