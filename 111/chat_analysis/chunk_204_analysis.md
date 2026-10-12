Ошибка, которую вы видите, связана с отсутствием команды `python` в системе. В большинстве современных Linux-дистрибутивов (например, Ubuntu/Debian) по умолчанию используется Python 3, и команда `python` не установлена. Вместо этого используется `python3`. 

### Решение:
1. **Используйте `python3` вместо `python`:**
   Замените команду `python` на `python3` в вашем скрипте. Например:
   ```bash
   python3 - <<'PY'
   import psycopg2
   ...
   ```

2. **Убедитесь, что Python 3 установлен:**
   Если `python3` также не найден, установите Python 3:
   ```bash
   sudo apt update
   sudo apt install python3
   ```

3. **Установите `psycopg2`:**
   Если вы получаете ошибки, связанные с отсутствием библиотеки `psycopg2`, установите её:
   ```bash
   pip3 install psycopg2-binary
   ```

4. **Проверьте установку:**
   После исправления команды и установки зависимостей вы можете запустить скрипт снова.

### Пример исправленного скрипта:
```bash
python3 - <<'PY'
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="lora",
    dbname="photobase",
)

cur = conn.cursor()

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

print("TABLES:")
for row in cur.fetchall():
    print(row[0])

cur.close()
conn.close()
```

Это должно отобразить список таблиц в вашей базе данных PostgreSQL.