Вот как сократить вывод:

1. **Последние 100 строк:**
```bash
команда 2>&1 | tail -100
```

2. **Только ошибки:**
```bash
команда 2>&1 | grep -iE 'error|fail|exception|traceback' -C 5
```

3. **Сохранить в файл:**
```bash
команда 2>&1 | tee /tmp/output.txt
```

**Для диагностики проекта:**
- Загрузи `/tmp/output.txt` (полный лог)
- Или последние 100–200 строк + участок с ошибкой

**Пример:**
```bash
python scripts/run_hybrid_v12.py 2>&1 | tail -200 | grep -iE 'error|fail' -C 5
```