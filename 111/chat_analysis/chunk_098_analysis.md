```bash
cd ~/projects/scene_fingerprint_mvp_v02 && \
python3 - <<'PY'
from pathlib import Path

p = Path("app/web/components/technical_modules/users.py")
s = p.read_text()

# Убираем цветовые кнопки и оставляем только пипетку
s = s.replace(
    '                        with ui.row().classes(\n                            "items-center gap-1 mt-1"\n                        ):\n\n                            for palette_color in USER_COLORS[\n                                :palette_count\n                            ]:\n\n                                is_selected = (\n                                    color.upper()\n                                    == palette_color.upper()\n                                )\n\n                                ui.button(\n                                    "",\n                                    on_click=lambda e,\n                                    uid=user_id,\n                                    c=palette_color:\n                                        apply_color(\n                                            uid,\n                                            c,\n                                        ),\n                                ).props(\n                                    "round"\n                                ).style(\n                                    f"""'
    '',
    ''
)

s = s.replace(
    '                                custom_color = ui.color_input(\n                                    value=color,\n                                ).props(\n                                    "round"\n                                ).classes(\n                                    "ml-1"\n                                )\n\n                                custom_color.on(\n                                    "update:model-value",\n                                    lambda e,\n                                    uid=user_id:\n                                        apply_color(\n                                            uid,\n                                            e.args\n                                            if isinstance(\n                                                e.args,\n                                                str\n                                            )\n                                            else e.value,\n                                        ),\n                                )',
    '                                custom_color = ui.color_input(\n                                    value=color,\n                                ).props(\n                                    "round"\n                                ).classes(\n                                    "ml-1"\n                                )\n\n                                custom_color.on(\n                                    "update:model-value",\n                                    lambda e,\n                                    uid=user_id:\n                                        apply_color(\n                                            uid,\n                                            e.args\n                                            if isinstance(\n                                                e.args,\n                                                str\n                                            )\n                                            else e.value,\n                                        ),\n                                )'
)

p.write_text(s)
PY

python3 -m py_compile app/web/components/technical_modules/users.py && \
echo "OK: цветовые кнопки удалены, осталась только пипетка"
```

После перезапуска:

```bash
cd ~/projects/scene_fingerprint_mvp_v02 && uv run python -m app.web.main
```

Теперь в разделе "Пользователи" будет только **пипетка** для выбора цвета, без сжатых кругов.