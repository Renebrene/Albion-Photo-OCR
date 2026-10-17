# Ручное исправление юридического адреса фото

Дата: 2026-10-17

## Зачем

DINO/HYBRID иногда распознаёт адрес неверно. В карточке фото владелец
(Администратор/Менеджер) может выбрать правильный адрес из справочника;
исправление хранится в базе и имеет приоритет над результатом распознавания.

## Модель данных

`schema/041_photo_address_overrides.sql`:

```sql
photo_address_overrides (
    photo_id   TEXT PRIMARY KEY REFERENCES photos(photo_id) ON DELETE CASCADE,
    address_id INTEGER NOT NULL REFERENCES address_directory(address_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
)
```

Результаты DINO/HYBRID и оригиналы не изменяются. Удаление строки возвращает
распознанный адрес.

## Как учитывается

`repository._PHOTO_DERIVED` подмешивает override и подставляет его
`legal_address`/`simple_address` вместо распознанных (COALESCE приоритет у
override). Фильтр по адресу (`list_photos(addresses=...)`) также находит фото
по любому активному fingerprint выбранного адреса, поэтому исправленное фото
попадает в свою адресную подборку.

Счётчик в панели «Адреса» (`list_addresses`) относит исправленное фото к
активному слепку адреса. Representative выбирается только среди
`fingerprints.active = true`: иначе при двух привязках (скрытый старый слепок и
активный новый) override уходил в скрытый, его строка исчезала из панели, и
счётчик активного слепка показывал 0 при непустой адресной подборке.

## API

| Метод | Путь | Scope | Назначение |
|---|---|---|---|
| PUT | `/v1/photos/{photo_id}/address` | `addresses:write` | `{address_id}` — поставить/заменить исправление |
| DELETE | `/v1/photos/{photo_id}/address` | `addresses:write` | снять исправление |

`GET /v1/photos/{photo_id}/details` возвращает `address_override` (или `null`).

## UI

В карточке фото у «Юридический адрес» есть кнопка с карандашом. Диалог
показывает список адресов справочника (`GET /v1/addresses/directory`),
сохраняет выбор и обновляет грид; при наличии исправления виден бейдж
«исправлено вручную» и кнопка «Сбросить».
