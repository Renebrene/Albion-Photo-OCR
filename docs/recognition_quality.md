# Вкладка «Качество распознавания»

Вкладка технического раздела отображает опубликованный снимок офлайн-оценки DINO/HYBRID. Это **не live-статистика production** и не запускает inference или эксперимент при открытии.

## Источник и API

- API: `GET /api/v1/recognition-quality` (обычный `read` scope).
- Источник по умолчанию: `data/reports/recognition_quality/snapshot.json`; фиксированный путь можно переопределить через `SCENE_RECOGNITION_QUALITY_SNAPSHOT`.
- Endpoint читает только JSON-файл, не обращается к PostgreSQL и не принимает имя/путь от клиента. Отсутствующий или некорректный снимок даёт `503` с безопасным сообщением.
- UI не читает CSV/Markdown и не выводит локальные пути.

## Схема снимка, версия 1

Снимок содержит:

- `schema_version`, `generated_at`, заголовок;
- `source`: имя эксперимента, исходные run/sample counts, относительные пути исходных файлов, label method, normalization, явные флаги manual labels / temporal holdout и notes;
- `totals`: полная выборка, размеченная и без однозначной метки;
- `variants`: каждый вариант с собственным знаменателем (`labelled`), `correct`, `wrong`, `review`, `accuracy`, delta к production и направленными `wrong_pairs`;
- `address_metrics_source`: полный per-address отчёт/знаменатель run-а, правило отбора (`selection`) и числа `total_addresses` / `selected_addresses`;
- `addresses`: все адреса отчёта с долей ошибок более 5% — per-address counts, размер активного fingerprint и top confusion pairs. `classification` различает `recognition_error`, `naming_variant` и `label_error`; варианты названия содержат `canonical_address_id`/`canonical_name` и не входят в число сомнительных. В текущем снимке так размечены строки 1–14 и 17–19, строка 29 — `label_error`.

`accuracy = correct / labelled`. Review и wrong — раздельные outcome; их нельзя смешивать. Per-address `error_rate = wrong / items`, где `items = correct + wrong + unknown`; `unknown` остаётся отдельным классом. Размер fingerprint — контекст, а не знаменатель оценки. `addresses` содержит только адреса с `error_rate > 0.05` (в текущем снимке 39 из 109 строк отчёта), а не весь адресный каталог и не все строки CSV; полный denominator адресного CSV указан в `address_metrics_source` и не должен выводиться из суммы отфильтрованных строк. `error_addresses`, `naming_variant_addresses` и `label_error_addresses` делят эти 39 строк на реальные ошибки (21), варианты названия (17) и ошибки в названии (1); общая accuracy эксперимента не пересчитывается. Loader отвергает неподдерживаемую schema version, несовпадающие счётчики и некорректные пары.

## Публикация/обновление снимка

1. Подготовить эксперимент в отдельном скрипте/копии. Не запускать inference или рескоринг из HTTP handler.
2. Использовать один и тот же фиксированный набор фото для всех сравниваемых вариантов; явно сохранять количество полного набора и размеченной части.
3. Проверить соответствие знаменателей исходным JSON/CSV, отдельно проверить `correct + wrong + review == labelled` для каждого варианта.
4. Для per-address отчёта проверить `correct + wrong + unknown == items` на каждом адресе; не считать адрес без активного слепка просто ошибкой модели.
5. Зафиксировать источник меток, правила canonicalization/aliases, метод, fingerprint/model version, параметры и `is_temporal_holdout`. Не маркировать filename-derived labels как ручную разметку.
6. Записать новый `snapshot.json` в этот фиксированный каталог. Не менять существующие сырые отчёты и runtime-данные; перед публикацией пройти тесты API/UI.

Снимок в репозитории на текущий момент построен из `comparison_combinations/report_run4.json` и `labeled_error_table/run4.csv`. У них **разные знаменатели**: варианты сравнения используют 31,983 размеченных фото, per-address таблица содержит 32,021 фото, включая 38 без результата. Интерфейс показывает эти источники отдельно. Результаты основаны преимущественно на эвристическом сопоставлении имени файла с текущим справочником; независимого temporal holdout в этом срезе нет. Снимки нельзя напрямую сравнивать с другим run, если sample, label method или знаменатель отличаются.

## Откат и эксплуатация

- Чтобы временно убрать данные с установки, переместить/не развёртывать snapshot; endpoint вернёт `503`, UI покажет сообщение. Кодовые маршруты и распознавание не изменяются.
- Никакой PostgreSQL migration не требуется.
- API показывает только агрегаты и адресные confusion counts; список исходных фото и их пути в MVP не публикуются.
