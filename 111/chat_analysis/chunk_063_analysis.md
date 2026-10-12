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

# Импорт SceneEmbedder
from src.recognizer.scene_embedder import SceneEmbedder

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
        })
    return result

def load_sub_embeddings():
    result = {}
    for fp in sorted(SUB_DIR.iterdir()):
        if not fp.is_dir():
            continue
        embeddings_path = fp / "embeddings.npy"
        if not embeddings_path.exists():
            continue
        try:
            embeddings = np.load(embeddings_path)
            result[fp.name] = embeddings
        except Exception as e:
            print(f"Error loading {fp.name}: {e}")
    return result

def calculate_similarity(query_emb, sub_emb):
    if sub_emb is None or query_emb is None:
        return 0.0
    # Косинусное сходство
    dot_product = np.dot(query_emb, sub_emb)
    norm_query = np.linalg.norm(query_emb)
    norm_sub = np.linalg.norm(sub_emb)
    if norm_query == 0 or norm_sub == 0:
        return 0.0
    return dot_product / (norm_query * norm_sub)

def main():
    print("="*80)
    print("SUB RERANK EXP V02")
    print("="*80)
    
    bench = load_json(BENCHMARK)
    sub_metadata = load_sub_metadata()
    sub_embeddings = load_sub_embeddings()
    
    print("images:", len(bench["results"]))
    print("sub groups:", len(sub_metadata))
    
    changed = 0
    results = []
    
    embedder = SceneEmbedder()
    
    for row in bench["results"]:
        file_path = row["file"]
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue
        
        try:
            query_emb = embedder.get_embedding(file_path)
        except Exception as e:
            print(f"Error getting embedding for {file_path}: {e}")
            continue
        
        candidates = []
        for k in ("top1", "top2", "top3", "top4", "top5"):
            if row.get(k):
                candidates.append(normalize(row[k]))
        
        best_sub = None
        best_score = 0.0
        
        for candidate in candidates:
            if candidate not in sub_metadata:
                continue
            for sub in sub_metadata[candidate]:
                sub_id = sub["id"]
                if sub_id in sub_embeddings:
                    sub_emb = sub_embeddings[sub_id]
                    score = calculate_similarity(query_emb, sub_emb)
                    if score > best_score:
                        best_score = score
                        best_sub = f"{candidate}_{sub_id}"
        
        old = row.get("top1")
        old_score = row.get("top1_score", 0)
        
        results.append({
            "file": row["file"],
            "old": old,
            "old_score": old_score,
            "new": best_sub,
            "new_score": best_score,
            "candidates": candidates,
        })
        
        if best_sub != old:
            changed += 1
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({
            "results": results,
            "changed": changed,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print()
    print("changed:", changed)
    print("saved:", OUT)

if __name__ == "__main__":
    main()
```

**Объяснение:**
1. **Загрузка данных:** Скрипт загружает данные из `benchmark.json` и метаданные подкластеров.
2. **Эмбеддинги:** Использует `SceneEmbedder` для получения эмбеддингов изображений.
3. **Сходство:** Вычисляет косинусное сходство между эмбеддингом изображения и эмбеддингами подкластеров.
4. **Результаты:** Сохраняет результаты в JSON-файл, показывая старые и новые значения, а также прирост точности.

**Ожидаемый вывод:**
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

Этот скрипт позволит оценить, насколько подкластеризация улучшает точность распознавания.