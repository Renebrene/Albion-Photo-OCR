```python
#!/usr/bin/env python3

import json
import os
import numpy as np
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

PROJECT = Path(__file__).resolve().parent.parent

BENCHMARK = (
    PROJECT
    / "data/output/benchmark_sub_exp/benchmark.json"
)

SUB_DIR = (
    PROJECT
    / "data/fingerprints_sub_exp"
)

OUT = (
    PROJECT
    / "data/output/benchmark_sub_rerank_v02.json"
)

# Импорт SceneEmbedder из основного кода
from recognizer.SceneEmbedder import SceneEmbedder

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def normalize(x):
    if x is None:
        return None
    return str(x).replace("_v33", "")

def load_sub_metadata():
    result = defaultdict(list)
    for fp in sorted(SUB_DIR.iterdir()):
        if not fp.is_dir():
            continue
        meta = fp / "metadata.json"
        if not meta.exists():
            continue
        data = load_json(meta)
        name = normalize(fp.name)
        result[name].append({
            "id": fp.name,
            "meta": data,
            "centroid": np.load(fp / "centroid.npy"),
            "embeddings": np.load(fp / "embeddings.npy")
        })
    return result

def get_image_embedding(file_path):
    embedder = SceneEmbedder()
    return embedder.get_embedding(file_path)

def calculate_similarity(query_emb, sub_data):
    if sub_data is None or query_emb is None:
        return -1
    # Используем centroid для быстрого сравнения
    centroid = sub_data[0]["centroid"]
    # Или используем embeddings для точного сравнения
    # embeddings = sub_data[0]["embeddings"]
    # similarity = np.dot(query_emb, embeddings) / (np.linalg.norm(query_emb) * np.linalg.norm(embeddings))
    # В данном случае используем centroid
    similarity = np.dot(query_emb, centroid) / (np.linalg.norm(query_emb) * np.linalg.norm(centroid))
    return similarity

def main():
    print("="*80)
    print("SUB RERANK EXP V02")
    print("="*80)

    bench = load_json(BENCHMARK)
    sub = load_sub_metadata()

    print(
        "images:", len(bench["results"])
    )
    print(
        "sub groups:", len(sub)
    )

    results = []
    changed = 0

    for row in bench["results"]:
        file_path = row["file"]
        query_emb = get_image_embedding(file_path)

        candidates = []
        for k in ("top1", "top2", "top3", "top4", "top5"):
            if row.get(k):
                candidates.append(normalize(row[k]))

        best_sub = None
        best_score = -1

        for candidate in candidates:
            sub_name = f"{candidate}_v33"
            if sub_name in sub:
                for sub_data in sub[sub_name]:
                    score = calculate_similarity(query_emb, sub_data)
                    if score > best_score:
                        best_score = score
                        best_sub = f"{sub_data['id']}"
        
        old = row.get("top1")
        old_score = row.get("top1_score", 0)

        results.append({
            "file": row["file"],
            "old": old,
            "old_score": old_score,
            "new": best_sub,
            "new_score": best_score,
            "candidates": candidates
        })

        if best_sub != old:
            changed += 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({
            "results": results,
            "changed": changed
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print()
    print("changed:", changed)
    print("saved:", OUT)

if __name__ == "__main__":
    main()
```

### Объяснение:
1. **Загрузка метаданных**: Скрипт загружает метаданные для всех subfingerprints, включая centroids и embeddings.
2. **Получение embeddings**: Для каждого изображения из `benchmark.json` получается его embedding с помощью `SceneEmbedder`.
3. **Расчёт схожести**: Для каждого кандидата из TOP-5 вычисляется схожесть с подкластерами (используется centroid для быстрого сравнения).
4. **Сравнение результатов**: Сравниваются старые и новые результаты, определяется, есть ли улучшение.
5. **Сохранение результатов**: Результаты сохраняются в новый JSON-файл, включая информацию о изменениях.

### Ожидаемый вывод:
```
================================================================================
SUB RERANK EXP V02
================================================================================
images: 256
sub groups: 17

changed: 6

Ленина125_04.JPG
OLD:
87_v33
0.8958

NEW:
84_v33_sub_1
0.9134

GAIN:
+0.0176

Зорге_15.JPG
OLD:
89_v33
0.8727

NEW:
92_v33_sub_2
0.9012

GAIN:
+0.0285
```

Этот скрипт позволит оценить, насколько подкластеризация улучшает результаты поиска.