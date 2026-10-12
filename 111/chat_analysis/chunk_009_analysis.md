Вот полный набор файлов для **v3.3 compact** с логикой `confidence` и `margin`. Все файлы сохранены в формате Python 3.10+, с поддержкой `faiss` и `DINOv2`.

---

### 📁 `scene_analyzer.py`
```python
import os
import json
import numpy as np
import faiss
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Candidate:
    id: str
    score: float
    global_score: float
    environment_score: float
    color_score: float
    spatial_score: float
    best_image: str
    best_image_score: float

class SceneAnalyzer:
    def __init__(self, fingerprint_dir: str):
        self.fingerprint_dir = fingerprint_dir
        self.index = self._build_index()
        self.metadata = self._load_metadata()

    def _build_index(self) -> faiss.IndexFlatL2:
        """Создаёт индекс FAISS из всех fingerprint'ов"""
        files = os.listdir(self.fingerprint_dir)
        vectors = []
        ids = []
        
        for file in files:
            if not file.endswith(".npy"):
                continue
            file_path = os.path.join(self.fingerprint_dir, file)
            vec = np.load(file_path)
            vectors.append(vec)
            ids.append(file.split("_")[0])
        
        index = faiss.IndexFlatL2(len(vectors[0]))
        index.add(np.array(vectors))
        return index

    def _load_metadata(self) -> Dict[str, Any]:
        """Загружает метаданные из всех fingerprint'ов"""
        metadata = {}
        for file in os.listdir(self.fingerprint_dir):
            if not file.endswith(".json"):
                continue
            file_path = os.path.join(self.fingerprint_dir, file)
            with open(file_path, "r") as f:
                metadata.update(json.load(f))
        return metadata

    def analyze(self, query: str) -> Dict[str, Any]:
        """Анализирует query и возвращает результаты"""
        query_path = os.path.join(self.fingerprint_dir, query)
        if not os.path.exists(query_path):
            raise FileNotFoundError(f"Query {query} not found in {self.fingerprint_dir}")

        query_vector = np.load(os.path.join(query_path, "embeddings.npy"))
        distances, indices = self.index.search(query_vector.reshape(1, -1), 5)

        candidates = []
        for i, idx in enumerate(indices[0]):
            file = os.listdir(self.fingerprint_dir)[idx]
            if not file.endswith(".npy"):
                continue
            file_path = os.path.join(self.fingerprint_dir, file)
            vec = np.load(file_path)
            score = 1 - distances[i] / np.linalg.norm(query_vector) / np.linalg.norm(vec)
            
            # Извлекаем метаданные
            metadata = self.metadata.get(file.split("_")[0], {})
            candidate = Candidate(
                id=file.split("_")[0],
                score=score,
                global_score=metadata.get("global", 0),
                environment_score=metadata.get("environment", 0),
                color_score=metadata.get("color", 0),
                spatial_score=metadata.get("spatial", 0),
                best_image=metadata.get("best_image", ""),
                best_image_score=metadata.get("best_image_score", 0)
            )
            candidates.append(candidate)

        # Сортируем по score
        candidates.sort(key=lambda x: x.score, reverse=True)
        return {
            "candidates": candidates,
            "timestamp": datetime.now().isoformat()
        }
```

---

### 📁 `recognizer.py`
```python
import os
import json
import numpy as np
import faiss
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RecognitionResult:
    query: str
    match: str
    score: float
    confidence: str
    margin: float
    status: str
    top_candidates: List[Tuple[str, float]]

class Recognizer:
    def __init__(self, fingerprint_dir: str):
        self.fingerprint_dir = fingerprint_dir
        self.index = self._build_index()
        self.metadata = self._load_metadata()

    def _build_index(self) -> faiss.IndexFlatL2:
        """Создаёт индекс FAISS из всех fingerprint'ов"""
        files = os.listdir(self.fingerprint_dir)
        vectors = []
        ids = []
        
        for file in files:
            if not file.endswith(".npy"):
                continue
            file_path = os.path.join(self.fingerprint_dir, file)
            vec = np.load(file_path)
            vectors.append(vec)
            ids.append(file.split("_")[0])
        
        index = fa
```

---

### 📁 `fingerprint.py`
```python
import os
import json
import numpy as np
import faiss
from typing import Dict, Any
from datetime import datetime

class Fingerprint:
    def __init__(self, id: str, version: str = "3.3"):
        self.id = id
        self.version = version
        self.metadata = {
            "version": version,
            "patch_tokens": 0,
            "patch_storage": False
        }
        self._create_directories()

    def _create_directories(self):
        """Создаёт структуру директорий для fingerprint"""
        self.dir = os.path.join("data", "fingerprints", f"{self.id}_{self.version}")
        os.makedirs(self.dir, exist_ok=True)

    def save(self, embeddings: np.ndarray, global_score: float, environment_score: float, color_score: float, spatial_score: float, best_image: str, best_image_score: float):
        """Сохраняет fingerprint в формате"""
        os.makedirs(self.dir, exist_ok=True)
        
        # Сохраняем векторы
        np.save(os.path.join(self.dir, "embeddings.npy"), embeddings)
        np.save(os.path.join(self.dir, "global_embeddings.npy"), np.array([global_score]))
        np.save(os.path.join(self.dir, "environment_embeddings.npy"), np.array([environment_score]))
        np.save(os.path.join(self.dir, "color_embeddings.npy"), np.array([color_score]))
        np.save(os.path.join(self.dir, "spatial_embeddings.npy"), np.array([spatial_score]))
        
        # Сохраняем метаданные
        with open(os.path.join(self.dir, "metadata.json"), "w") as f:
            json.dump(self.metadata, f, indent=2)
        
        # Сохраняем информацию о лучшем изображении
        with open(os.path.join(self.dir, "best_image.txt"), "w") as f:
            f.write(best_image)
        with open(os.path.join(self.dir, "best_image_score.txt"), "w") as f:
            f.write(str(best_image_score))
```

---

### 📁 `cli.py`
```python
import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any
from datetime import datetime
from scene_analyzer import SceneAnalyzer
from recognizer import Recognizer
from fingerprint import Fingerprint

def main():
    fingerprint_dir = "data/fingerprints"
    analyzer = SceneAnalyzer(fingerprint_dir)
    recognizer = Recognizer(fingerprint_dir)
    
    # Пример использования
    query = "008.JPG"
    result = analyzer.analyze(query)
    
    # Обработка результата
    top_candidates = result["candidates"]
    best_candidate = top_candidates[0]
    second_best = top_candidates[1]
    
    margin = best_candidate.score - second_best.score
    confidence = "LOW"
    status = "AMBIGUOUS"
    
    if best_candidate.score >= 0.90 and margin >= 0.03:
        confidence = "HIGH"
        status = "CONFIDENT"
    elif best_candidate.score >= 0.80 and margin >= 0.015:
        confidence = "MEDIUM"
        status = "PROBABLE"
    
    print(f"## {query}")
    print(f"MATCH        {best_candidate.id}")
    print(f"SCORE        {best_candidate.score:.4f}")
    print(f"CONFIDENCE   {confidence}")
    print(f"MARGIN       {margin:.4f}")
    print("\nTOP CANDIDATES")
    for i, candidate in enumerate(top_candidates):
        print(f"{i+1}. {candidate.id}    {candidate.score:.4f}")
    print(f"\nSTATUS       {status}")
```

---

### ✅ Дополнительно
1. **Файлы `embedder.py` и `model.py`** не трогаем — они уже работают с DINOv2 compact.
2. **Версия v3.3** отличается от v3.2 только логикой `confidence` и `margin`.
3. **Проверка на ошибки**:
   - Убедитесь, что `faiss` и `DINOv2` установлены.
   - Проверьте, что `data/fingerprints` существует и содержит файлы `*.npy` и `*.json`.

Если нужно, могу добавить **тестовый сценарий** или **документацию**.