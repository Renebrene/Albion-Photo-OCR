### 🤖 **Assistant** — 2026-08-15 03:06:33

Отлично, что ты уже сделал `diff`. Теперь давай посмотрим на **точные изменения** в `compare()`.

Сначала **размеры и количество строк**:

```bash
wc -l /tmp/scene_analyzer_diff.txt
```

Если выйдет, например:

```text
1234 /tmp/scene_analyzer_diff.txt
```

значит, **изменилось около 1200 строк** — это уже серьёзная переработка.

Теперь посмотрим на **формулу `final_score`**:

```bash
cat /tmp/scene_analyzer_diff.txt | grep -E 'global_score|environment_score|color_score|spatial_score|final_score'
```

Если выйдет что-то вроде:

```text
--- a/scene_analyzer.py.backup_before_optimization
+++ b/scene_analyzer.py
@@ -390,10 +390,12 @@ def compare(
     query_global=None,
     query_environment=None,
     query_color=None,
+    query_spatial=None,
     query_spatial=None,
     ...
-    final_score = (
-        global_score * 0.4
-        + environment_score * 0.3
-        + color_score * 0.2
-        + spatial_score * 0.1
-    )
+    final_score = (
+        global_score * 0.3
+        + environment_score * 0.25
+        + color_score * 0.2
+        + spatial_score * 0.25
+    )
```

то это **очевидная причина деградации** — **коэффициенты изменились**.

Если же:

```text
--- a/scene_analyzer.py.backup_before_optimization
+++ b/scene_analyzer.py
@@ -390,10 +390,10 @@ def compare(
     query_global=None,
     query_environment=None,
     query_color=None,
-    query_spatial=None,
+    query_spatial=None,
     ...
-    final_score = (
-        global_score * 0.4
-        + environment_score * 0.3
-        + color_score * 0.2
-        + spatial_score * 0.1
-    )
+    final_score = (
+        global_score * 0.4
+        + environment_score * 0.3
+        + color_score * 0.2
+        + spatial_score * 0.1
+    )
```

то проблема **в другом** — возможно, **оптимизация изменила, как данные передаются в `compare()`**, а не формулу.

### Что делать дальше

Если **коэффициенты изменились**, то:

1. **Восстанови старую формулу** в `scene_analyzer.py`.
2. **Оставь ThreadPoolExecutor** и другие оптимизации.
3. **Проверь, как данные передаются** в `compare()` — возможно, нужно вернуть старый способ получения `environment`, `color`, `spatial`.

Если **коэффициенты не изменились**, то:

1. **Проверь, как оптимизированный recognizer передает данные** в `compare()` — возможно, **неправильно нормализует или фильтрует** значения.
2. **Сравни с backup_before_optimization**, чтобы понять, что именно изменилось.

Пришли выводы из `diff` — по ним я дам точную инструкцию, что делать дальше.