### ✅ **Замена `build_photo_index()`**

Вот как будет выглядеть обновлённая функция:

```python
def build_photo_index():

    # Очистим старый индекс
    PHOTO_INDEX.clear()

    # Получаем все записи из PostgreSQL
    records = get_all_photos_from_db()

    # Группируем по виртуальному адресу (или dino_fingerprint)
    for record in records:

        # Путь к файлу (физический)
        source_path = record.get("source_path")

        # Виртуальный адрес (пока используем hybrid_final_id, если есть)
        virtual_address = record.get("hybrid_final_id") or record.get("dino_fingerprint")

        # Если нет виртуального адреса — оставляем в отдельной группе
        if not virtual_address:
            virtual_address = "no_address"

        # Проверяем, существует ли файл (в будущем это можно убрать)
        path = Path(source_path)
        if not path.exists():
            continue

        # Создаём запись в PHOTO_INDEX
        PHOTO_INDEX[virtual_address].append({
            "path": path,
            "db_record": record,
            "virtual_address": virtual_address,
        })

    # Обновляем фильтры
    update_photo_filters()
```

---

### 🔁 **Что это даёт**

- **Физические файлы не копируются** — мы просто используем их из `data/input/daily`.
- **Виртуальный адрес** теперь определяется из БД (`hybrid_final_id` или `dino_fingerprint`).
- **Фотографии без fingerprint** попадают в группу `no_address`, чтобы не исчезли из грида.
- **Фильтры по адресам/клиентам** остаются рабочими, потому что они используют `STATE.selected_addresses`.

---

### 🧠 **Дополнительные замечания**

- Если вы хотите убрать группу `no_address`, можно добавить проверку:
  ```python
  if virtual_address == "no_address":
      continue
  ```
- В будущем можно перейти к чистому PostgreSQL-индексу, убрав `PHOTO_INDEX` и используя только `db_record`.

---

### ✅ **Далее**

После этого вы можете:

1. **Проверить, что фото отображаются** в UI по виртуальным адресам.
2. **Создать новый этап** для запуска Hybrid v12 и записи в БД.
3. **Подключить `hybrid_final_id`** к UI как основной адрес.

Если нужно, я могу помочь с реализацией следующего этапа.