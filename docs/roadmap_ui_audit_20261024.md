# Дорожная карта по итогам UI-аудита — 2026-10-24

## Срез

- Ветка: `feature/video-ingest-editor-layout`. Срез аудита: `ecbd116` (текущий HEAD ветки может быть новее — перед началом этапа сверить строки).
- Объём аудита: `frontend/src` (~17,6 тыс. строк, 83 файла) + `src/api/client.js`; ядро (`PhotosGrid.vue`, `stores/photos.js`, `VideosGrid.vue`, `stores/videos.js`, `client.js`, `CollectionsPanel.vue`) разобрано вручную, периферия — четырьмя параллельными аудиторами.
- Тесты на момент аудита: **32 файла / 266 тестов Vitest — все зелёные**. Код в ходе аудита не менялся.
- Все ссылки «файл:строки» даны на срез `ecbd116`; при переносе строк сверять по смыслу.

## Как читать

| Приоритет | Смысл |
|---|---|
| **P0** | Функция реально не работает / теряются действия пользователя / фоновые утечки и гонки, заметные в эксплуатации |
| **P1** | Двойные действия, race conditions, необратимые действия без подтверждения, скрытие UI при ошибке |
| **P2** | UX-полировка, производительность, мелкие дефекты |

Всего 50 находок: **P0 — 8, P1 — 20, P2 — 22**. Каждый пункт содержит: что не так, что сделать, какой тест добавить.

Процесс: один этап = один набор коммитов; после зелёных тестов — push в `main`; после UI-изменений — Ctrl+F5 и проверка build-stamp в подвале. Не смешивать фиксы из разных этапов в одном коммите.

---

## Этап 1 — P0 (8)

### Пакет 1.1. `AuthImage`: lazy-режим и лишний трафик

`src/components/AuthImage.vue:124-145,176` (+ `src/pages/PhotosGrid.vue:3185-3189`)

- [ ] Перенести `ref="rootEl"` с ветки `v-else-if="lazy"` на постоянный корень (`.auth-image-root` или стабильный wrapper): сейчас ветка при монтировании не рендерится (`usingBlob=false`), `observer.observe` никогда не вызывается, fallback сразу делает `visible=true; load(url)` — lazy не работает.
- [ ] Не вызывать `load()` в cookie-режиме: `<q-img :src="url">` уже грузит картинку, параллельный blob-fetch — двойной трафик и скрытая ссылка в `_imageCache`.
- [ ] Оставить blob-путь только для `usingBlob` (fallback по `onDirectError`) и для `lazy`-ветки.
- [ ] После исправления включить `lazy` у миниатюр list-режима `PhotosGrid.vue:3185-3189`.
- Тест (`tests/auth-image-lazy.spec.js`): заглушка `IntersectionObserver`; assert — без пересечения `fetch` не вызывается; после `isIntersecting` — вызывается один раз; при `usingBlob=false` blob-fetch не выполняется; `releaseImageUrl` вызван на unmount.
- DoD: в Network одного грида на ~100 плиток нет двойных загрузок; прокрутка ниже вьюпорта не тянет превью.

### Пакет 1.2. `videos.js`: потеря сброса фильтра

`src/stores/videos.js:24-31` (+ `src/pages/VideosGrid.vue:98-105`)

- [ ] Заменить `if (this.loading) return` на счётчик поколения: новый вызов инкрементирует `seq`; устаревший ответ не пушит `items`/`nextCursor`; `reset` всегда выполняется.
- Тест (`tests/videos-store-filter-reset.spec.js`): два последовательных `loadPage` — второй с `reset:true` при «летящем» первом; assert — в store данные только по новому фильтру, старый ответ отброшен.
- DoD: смена даты/поиска во время прокрутки всегда применяет фильтр.

### Пакет 1.3. Busy-защита действий

- [ ] `src/pages/Settings.vue:352-403,464-487` (кнопки 671-674, 745-775): `runAll`, `retryFailed`, `stopQueue`, `clearQueue`, `unload`, `clearKey` — busy-ref + `:loading`, сброс в `finally`.
- [ ] `src/components/UsersAdmin.vue:47-61,89-111,119-129,63-70`: guard во всех формах (создание, правка, пароль, toggleActive).
- [ ] `src/components/FingerprintsList.vue:491-523,839`: `editBusy` на «Сохранить» (иначе два пересчёта базы).
- [ ] `src/components/FingerprintsList.vue:525-540,680-689`: per-row busy (`Set` по `fingerprint_id`) для тумблера `active`.
- [ ] `src/components/AddressDirectory.vue:120-135,169-206`: `saving` для «Сохранить»/«Сохранить сопоставление».
- [ ] `src/pages/Processing.vue:323-338,553-563`: `hybridStarting` для `startHybrid` (по образцу `starting`).
- [ ] `src/pages/PhotosGrid.vue:1951-1988` (кнопка 2869-2879): busy для «Скачать» (сейчас параллельные циклы закачек).
- [ ] `src/pages/PhotosGrid.vue:1717-1730,4028,4053`: busy для «Сохранить» в диалогах подборки и Избранного.
- Тест (`tests/async-action-guard.spec.js`): двойной вызов обработчика при неразрешённом промизе отправляет ровно один запрос.
- DoD: ни один обработчик этапа не выполняет два запроса при двойном клике.

### Пакет 1.4. `FingerprintsList`: жизненный цикл опроса

`src/components/FingerprintsList.vue`

- [ ] `381-394,412-441`: отмена циклов `pollBatch`/`pollBuild` при уходе со страницы (токен поколения или AbortController); запретить `load()`/`Notify` после unmount.
- [ ] `128-137,268-276,417,384,1062`: `openBuild`/`openBatch` инкрементируют токен опроса — старый цикл не «воскрешает» `buildJob`/`batchState`, кнопка «Собрать» не блокируется зомби-статусом; `resumeBuild` не запускает второй цикл.
- [ ] `416,384,118-120,1062`: try/catch на каждой итерации polling с 2–3 ретраями; ошибка фиксируется в state, цикл не рвётся навсегда.
- [ ] `268-276,356-378,1141-1142,1290-1296`: сброс `batchBusy` в `openBatch`.
- Тест (`tests/fingerprints-poll-lifecycle.spec.js`): «закрыть и открыть другой слепок» — нет чужих обновлений; «ошибка сети на 3-й итерации» — опрос продолжается; «unmount во время poll» — запросов больше нет.
- DoD: после закрытия диалога/ухода со страницы фоновых запросов нет; кнопка «Собрать» всегда разблокируется.

### Пакет 1.5. `Automation.vue`: автосохранение на каждый ввод

`src/components/Automation.vue:77-87,170-192,194-199`

- [ ] Убрать PUT на `@update:model-value`; редактировать локальную копию, сохранять по debounce (≥500 мс после последнего ввода) или кнопке.
- [ ] Response-token: старый ответ не перетирает новое значение.
- [ ] Не блокировать поле, которое редактируется (`:disable="busy"` не должен мешать набору).
- Тест (`tests/automation-autosave.spec.js`): ввод «30» даёт один PUT со значением 30 (после debounce), промежуточное 3 не уходит.
- DoD: планировщик никогда не получает промежуточный интервал.

**Выход этапа 1:** все тесты зелёные (266 + новые), ручная проверка: сетка, диалог слепков, видео-фильтры, страница настроек.

---

## Этап 2 — P1 (20)

### 2.1. Ошибки и гонки данных

- [ ] `src/api/client.js:83-101,36-37`: `_imageRecent` ограничить по суммарному размеру (LRU ~32–64 МБ) или не класть туда крупные blob (оригиналы) — сейчас десятки открытых оригиналов держат сотни МБ.
- [ ] `src/pages/PhotosGrid.vue:2109-2128`: привести код к комментарию — полный `refresh()` только если адрес входит в активный фильтр; убрать дубль `loadAddresses` (2124 и 2127).
- [ ] `src/stores/pipeline.js:63-92,111-117`: `_clear()` только по валидному ответу `active=false`; при сетевой ошибке сохранять последнее состояние.
- [ ] `src/components/SystemMonitor.vue:28-44`: in-flight guard или самоперепланирующийся `setTimeout` после ответа.
- [ ] `src/pages/Settings.vue:189-203` (+ `80-104`): при смене провайдера не перетирать несохранённые правки формы; обновлять только provider-specific поля.
- [ ] `src/pages/Processing.vue:525,292-297,57-76`: смена вкладки не должна стирать несохранённые пороги.
- [ ] `src/components/IngestFolder.vue:128-147`: захватить путь до `await` (`const target = path.value.trim()`), использовать его при записи результата.
- [ ] `src/components/FingerprintsList.vue:542-557`: request-token для `openVersions` (устаревший ответ не должен показать версии чужого слепка).

### 2.2. Деструктивные действия без подтверждения

- [ ] `src/components/CollectionsPanel.vue:59-66` — удаление подборки.
- [ ] `src/pages/PhotosGrid.vue:3001-3009` — удаление сохранённого поиска.
- [ ] `src/components/AddressDirectory.vue:147-155,330` — удаление адреса.
- [ ] `src/pages/Settings.vue:768-774` — «Очистить список заданий» (необратимо).
- Единый хелпер `confirmDestructive(text)` (п. «Архитектура») — подключить здесь.

### 2.3. Ошибки, скрывающие интерфейс

- [ ] `src/components/ClientNormalization.vue:42-64`: молчаливые catch → баннер ошибки с повтором; отличать «пусто» от «не загрузилось».
- [ ] `src/components/CloudLinkButton.vue:36-46`: ограниченные ретраи опроса, «Проверить ещё раз», метка «статус неизвестен» после лимита.
- [ ] `src/components/PipelineUpdateButton.vue:102-121,209-216,220,240-316` и `PipelineRunsPanel.vue:55-67,73`: скрывать блок только на устойчивом 404; прочие ошибки — сохранять последнее состояние + баннер/повтор.
- [ ] `src/components/VisitsAdmin.vue:16-28`: различать 404 «таблицы нет» и сетевые/403 ошибки.

### 2.4. Валидация форм

- [ ] `src/components/CloudSettings.vue:60-71,160-170`: `ttl_days` — целое ≥ 1, `:rules` на поле; `0` не должен молча превращаться в 90.
- [ ] `src/components/UsersAdmin.vue:47-61,89-99`: `:rules` на имя (непустое), `lazy-rules`.

### 2.5. Производительность

- [ ] `src/pages/PhotosGrid.vue:3193-3201,3219-3225,3230-3237`: `listMainParts`/`listSecondParts`/`listExtraFields` вызываются 3–5 раз на строку за рендер — вычислять один раз.
- [ ] `src/pages/PhotosGrid.vue:216-223,250-256`: `waitForQwenJob` — прекращать опрос при unmount/закрытии зрителя (см. общий poll-хелпер).

### 2.6. UX-обратная связь

- [ ] `src/components/FingerprintsList.vue:417,959-976`: передавать `progress` из ответа — прогресс-бар сборки сейчас всегда 0 %.
- [ ] `src/components/FingerprintsList.vue:200-211`: при `skipped` не ставить `buildJob` в PENDING (кнопка блокируется навсегда) либо продолжать опрос чужого job_id.
- [ ] `src/components/IngestFolder.vue:149-169,451-454`: отслеживать задание (статус/прогресс/отмена), не показывать вечное «выполняется воркером».

**Выход этапа 2:** тесты зелёные; ручная проверка: удаления требуют подтверждения; сетевые ошибки не прячут панели; правка адреса фото не сбрасывает прокрутку без необходимости.

---

## Этап 3 — P2 (22)

### 3.1. Мелкие логические дефекты

- [ ] `src/pages/PhotosGrid.vue:3531`: `current?.margin !== null` → `!= null` / `typeof === 'number'` (пустой блок у фото без runner-up).
- [ ] `src/pages/PhotosGrid.vue:4162`: убрать мёртвый `:loading="false"`; при желании — `:loading` на «Распознать заново».
- [ ] `src/pages/Settings.vue:688-701`: `stats.counts?.FAILED || 0`.
- [ ] `src/components/FingerprintsList.vue:179-187,343-349`: общая валидация ID (regex + уникальность) для одиночной сборки и батча.
- [ ] `src/utils/periodRange.js:64-65`: валидировать/нормализовать «с…по» (свап или блокировка применения).
- [ ] `src/components/CloudSettings.vue` — см. 2.4 (если не закрыто).

### 3.2. UX-полировка

- [ ] `src/pages/PhotosGrid.vue:1329-1333`: `scrollToTop()` после `refreshGrid()`.
- [ ] `src/components/DisplaySettings.vue:108-117`: подтверждение сброса настроек отображения.
- [ ] `src/components/FingerprintsList.vue:467-482`: сбрасывать кэш справочника адресов при монтировании.
- [ ] `src/pages/Settings.vue:595-603,106-127`: не перетирать ручной выбор модели в `loadModels`; busy для `clearKey`.
- [ ] `src/pages/Processing.vue:33,83-104,376-378`: очищать `previewTimer` в `onBeforeUnmount`.
- [ ] `src/pages/Processing.vue:86-103`: stale-guard для ответа `previewHybridSettings`.

### 3.3. Фоновые процессы

- [ ] `src/stores/pipeline.js:119-127` + `Processing.vue:370-373` + `SystemMonitor.vue:39` + `PipelineUpdateButton.vue:211`: пауза поллеров по `document.hidden`, немедленный refresh при возврате.
- [ ] `src/pages/PhotosGrid.vue:216-223,250-256`: см. 2.5 (если не закрыто).

### 3.4. Производительность (дополнительно)

- [ ] `src/stores/photos.js:446-453`: `loadAddresses`/`loadClients` после `refresh()` — параллельно (`Promise.allSettled`), оба уже токенизированы.

---

## Архитектурные улучшения

Вводить по мере этапов, не отдельным «большим рефакторингом».

1. **`useAsyncAction` (composable)** — guard от повторного входа + `:loading` + `finally`-сброс. Закрывает пакет 1.3 и большую часть 2.x механически. Внедрять в 1.3, дальше использовать везде.
2. **`usePolling` (хелпер)** — токен поколения, ограниченные ретраи с backoff, пауза по `visibilitychange`, отмена в `onBeforeUnmount`. Кандидаты: `pipeline.js`, `SystemMonitor`, `FingerprintsList` ×2, `CloudLinkButton`, будущий `IngestFolder`. Внедрять в 1.4, остальное перевести в этапе 3.
3. **`confirmDestructive(text)`** — единый диалог; подключить в 2.2 и 3.2.
4. **Поколения запросов в `videos.js`** — перенести паттерн из `photos.js` (пакет 1.2).
5. **Виртуализация грида** (`q-virtual-scroll`) — только после фикса `AuthImage`: сейчас грид держит все догруженные карточки в DOM; оценить на корпусе >500 плиток.
6. **Проверка размеров blob-кэша** — после 2.1 (`client.js`) добавить метрику/ограничение по байтам.

---

## Порядок и зависимости

1. **1.1 AuthImage** — самостоятелен, но затрагивает все сетки: делать первым и проверять оба режима (`usingBlob=false/true`).
2. **1.2 videos.js** — самостоятелен.
3. **1.3 busy** — сначала ввести `useAsyncAction`, затем перевести обработчики.
4. **1.4 FingerprintsList polling** — после введения `usePolling` (или с локальным токеном, если хелпер ещё не готов).
5. **1.5 Automation** — самостоятелен.
6. Этап 2 — после зелёного этапа 1; 2.1 (`client.js`) до этапа 3.
7. Этап 3 — по мере свободного времени; 3.3 после `usePolling`.

Зависимости между этапами: 1.1 → 3.4-виртуализация; 1.3 → 2.х busy-пункты; 1.4 → 3.3; 2.1 (`client.js`) → 3.х память.

---

## Тесты и критерии готовности

### Новые spec-файлы

- `tests/auth-image-lazy.spec.js` — lazy + отсутствие двойного fetch.
- `tests/videos-store-filter-reset.spec.js` — reset при in-flight запросе.
- `tests/async-action-guard.spec.js` — двойной клик → один запрос.
- `tests/fingerprints-poll-lifecycle.spec.js` — unmount/stale/ошибки опроса.
- `tests/automation-autosave.spec.js` — debounce и единый PUT.
- `tests/confirm-destructive.spec.js` — отмена в диалоге не отправляет DELETE.
- `tests/photos-grid-address-change.spec.js` — refresh только при активном адресном фильтре.

### DoD каждого этапа

- [ ] Новые и существующие тесты зелёные: базовая линия **266/266**.
- [ ] `git diff --check` без ошибок, `git status` содержит только файлы этапа.
- [ ] При изменении поведения UI — обновлены `docs/ui_changes_20261024.md` / `docs/frontend_quasar.md`.
- [ ] Ручная проверка: Ctrl+F5, build-stamp в подвале; оба режима `AuthImage`; гость (read-only) не получает новых действий.
- [ ] Push в `main` после зелёного этапа (standing rule владельца).

### Команды проверки

```bash
cd frontend
node node_modules/vitest/vitest.mjs run      # npx в окружении недоступен
# или: npm test
```

```bash
git diff --check && git status --short
```

---

## Вне scope

- Изменения бэкенда/API: все находки фронтендовые; формат `GET /v1/jobs/{id}` (поле `progress`) уже корректный.
- Миграции БД, работа с production-данными, повторный INGEST/DINO/HYBRID.
- Полноценная виртуализация и code-splitting — отдельное решение по замерам (п. «Архитектура», 5).
- Косметика вёрстки и тёмной темы — только если всплывёт при ручной проверке этапов.
