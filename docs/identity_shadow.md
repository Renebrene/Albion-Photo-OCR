# Теневая идентичность фото (metadata-v1)

Статус: **наблюдение, по умолчанию выключено.** `photo_id` и регистрация
не меняются; рядом с текущим SHA-256 считается будущий id и пишется в
локальный журнал.

## Зачем

Сейчас `photo_id = PH_ + SHA-256(файла)[:24]`. Хеш требует прочитать файл
целиком: 10.4 мс на фото локально и полный проход по сети. Камера при этом
уже пишет почти уникальный ключ:

`BodySerialNumber + DateTimeOriginal + SubSecTimeOriginal + размер файла`.

Замер на корпусе (1549 JPEG, 0.54 мс на файл):

| Показатель | Значение |
|---|---:|
| Полный ключ есть | 1545 |
| Без EXIF (нужен откат на SHA) | 4 |
| Групп одинаковых v2-id | 29 |
| Из них с **разным** содержимым | **0** |

Все 29 групп — побайтовые копии одного файла (переименованные/разложенные
по папкам). Ранее на том же корпусе проверено: если убрать размер файла из
ключа, появляется одна коллизия с разным содержимым, поэтому размер
обязателен. `ImageUniqueID` не используется: Canon пишет его в MakerNote,
который Pillow не разбирает.

## Как включить

```bash
SCENE_IDENTITY_SHADOW=1
# Необязательно; по умолчанию <SCENE_DATA>/logs/identity_shadow.jsonl
# SCENE_IDENTITY_SHADOW_LOG=/opt/scene-fingerprint/data/logs/identity_shadow.jsonl
```

Флаг читается процессом INGEST. После изменения окружения перезапустить
`scene-pipeline-worker` (или тот процесс, который выполняет ingest).

## Что пишется

Одна JSON-строка на каждый **новый** файл, прошедший INTEGRITY (уже
зарегистрированные файлы пропускаются до чтения, как и раньше):

```json
{"at":"2026-10-23T18:00:00+00:00","source_path":"/photos/a.JPG",
 "filename":"a.JPG","sha256":"…64 hex…","sha_photo_id":"PH_…24…",
 "v2_photo_id":"PH_…24…","v2_hash":"…64 hex…","scheme":"metadata-v1",
 "complete":true,"serial":"328055000461","taken_at":"2025-12-18 11:09:27",
 "subsec":"17","size_bytes":7624268}
```

- `complete=false` — не хватило serial/времени/сотых; после переключения
  такие файлы обязаны идти через SHA-фолбэк.
- Запись — один `os.write` с `O_APPEND`, поэтому несколько процессов INGEST
  не перемешивают строки. Ошибка журнала печатается в stderr и **никогда**
  не валит INGEST.

## Как проверить результат

```bash
python - <<'PY'
import json, collections
rows=[json.loads(l) for l in open("data/logs/identity_shadow.jsonl")]
by_id=collections.defaultdict(set)
for r in rows:
    by_id[r["v2_photo_id"]].add(r["sha256"])
print("файлов:", len(rows))
print("без полного ключа:", sum(not r["complete"] for r in rows))
print("v2-id с разным содержимым:", sum(len(v)>1 for v in by_id.values()))
PY
```

Критерий переключения: доля `complete` приемлема (для корпуса ~99.7 %),
коллизий с разным содержимым нет. После этого — миграция `photos`
(`identity_hash`, `identity_scheme`, `sha256` NULL-able) и переключение
регистрации, отдельным согласованным этапом.

## Откат

Выключить `SCENE_IDENTITY_SHADOW` и удалить журнал. Ни база, ни `photo_id`,
ни исходники не затрагиваются — откатывать нечего.
