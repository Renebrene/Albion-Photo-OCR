### ✅ **Замена в `main.py`**

Заменяем участок `ПЕРИОД + АДРЕСА + КЛИЕНТЫ + ФОТО` на следующий код:

```python
# ============================================================
# ОСНОВНАЯ ОБЛАСТЬ
#
#   ПЕРИОД
#   АДРЕСА | КЛИЕНТЫ | ФОТО
#
# Адреса и клиенты имеют одинаковую ширину и начинаются
# строго на одной горизонтальной линии.
# ============================================================

with ui.row().classes(
    "w-full px-3 gap-3"
).style(
    "height: calc(100vh - 120px);"
    "overflow: hidden;"
):

    # ========================================================
    # ПЕРИОД
    # ========================================================
    with ui.column().classes(
        "w-[580px] shrink-0"
    ).style(
        "margin: 0;"
    ):
        with ui.row().classes(
            "w-full items-center gap-3"
        ):
            ui.label(
                "Период"
            ).classes(
                "text-lg font-bold shrink-0"
            )

            ui.radio(
                [
                    "Дата съёмки",
                    "Дата загрузки",
                ],
                value="Дата загрузки",
            ).props(
                "dense inline"
            )

            ui.select(
                [
                    "Текущий месяц",
                    "Предыдущий месяц",
                    "Все даты",
                    "Выбрать период",
                ],
                value="Текущий месяц",
                label="Период",
            ).props(
                "dense outlined"
            ).classes(
                "w-52"
            )

    # ========================================================
    # АДРЕСА | КЛИЕНТЫ
    # ========================================================
    with ui.row().classes(
        "flex-1 flex flex-wrap gap-3"
    ).style(
        "overflow: hidden;"
    ):

        # ----------------------------------------------------
        # АДРЕСА
        # ----------------------------------------------------
        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full"
        ).style(
            "overflow: hidden;"
        ):
            with ui.column().classes(
                "w-full h-full min-h-0"
            ).style(
                "overflow-y: auto;"
            ):
                build_addresses(
                    lambda: STATE.refresh_photos()
                    if STATE.refresh_photos
                    else None
                )

        # ----------------------------------------------------
        # КЛИЕНТЫ
        # ----------------------------------------------------
        with ui.column().classes(
            "w-[280px] min-w-[280px] h-full"
        ).style(
            "overflow: hidden;"
        ):
            with ui.column().classes(
                "w-full h-full min-h-0"
            ).style(
                "overflow-y: auto;"
            ):
                build_clients_panel(
                    lambda: STATE.refresh_photos()
                    if STATE.refresh_photos
                    else None
                )

    # ========================================================
    # ФОТО
    # ========================================================
    with ui.column().classes(
        "flex-1 min-w-0 h-full"
    ).style(
        "overflow: hidden;"
    ):
        refresh_photos = build_photos()
        STATE.refresh_photos = refresh_photos
```

---

### ✅ **Что изменилось:**

1. **"Период" и "Фото" теперь на одной строке** — "Период" в отдельной колонке слева, а "Фото" — в правой колонке.
2. **"Адреса | Клиенты"** — теперь в отдельной строке, которая начинается на той же высоте, что и "Период".
3. **Подборки** — остаются внутри своих колонок, не дублируются и сохраняют скролл.
4. **Вертикальные скроллы** — сохранены для "Адреса" и "Клиенты".

---

### ✅ **Что не трогаем:**

- `build_search()` — остался вверху.
- `build_collections()` — остался в `components/collections.py`.
- `STATE` и `refresh_photos` — всё работает как раньше.

---

### ✅ **Дополнительно:**

Если хочешь, я могу сделать **CSS-стили** для улучшения визуала (например, границы между колонками), но это уже не часть логики.