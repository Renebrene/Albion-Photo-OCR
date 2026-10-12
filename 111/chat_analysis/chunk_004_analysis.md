```bash
#!/bin/bash

# 🛠️ Upgrade to v3.1: Environment-First Fingerprinting
# 📌 Maintains compatibility with v3, adds environment-weighted scoring

# 🔒 Backup current v3
echo "Backing up v3 files..."
cp -r fingerprint/ fingerprint_v3_backup
cp -r models/ models_v3_backup
cp -r logs/ logs_v3_backup

# 📁 Create v3.1 directory
mkdir -p fingerprint_v31 models_v31 logs_v31

# 📜 Copy base files
cp -r fingerprint/ fingerprint_v31/
cp -r models/ models_v31/
cp -r logs/ logs_v31/

# 🧠 Update embedder.py (v3.1 logic)
echo "Updating embedder.py for v3.1..."
cat > fingerprint_v31/embedder.py <<EOF
import torch
from torchvision import transforms
from models import DINOv2
from utils import load_image, get_environment_vectors

class Embedder:
    def __init__(self, model_path="models/dinov2_vits14.pt"):
        self.model = DINOv2.load(model_path)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
        ])

    def get_embeddings(self, image_path, environment_weight=0.5):
        image = load_image(image_path)
        image_tensor = self.transform(image).unsqueeze(0)
        
        # Get global and patch embeddings
        global_emb, patch_emb = self.model(image_tensor)
        
        # Get environment vectors
        env_vectors = get_environment_vectors(image_path)
        
        # Weighted combination
        final_emb = (
            0.15 * global_emb +
            0.25 * patch_emb +
            0.50 * torch.mean(env_vectors, dim=0) +
            0.10 * torch.mean(torch.stack([get_color_features(image_path)]), dim=0)
        )
        
        return final_emb
EOF

# 📜 Update fingerprint.py (v3.1 logic)
echo "Updating fingerprint.py for v3.1..."
cat > fingerprint_v31/fingerprint.py <<EOF
import os
import torch
from embedder import Embedder
from utils import get_environment_vectors, get_color_features

class Fingerprint:
    def __init__(self, id, embeddings, environment_vectors, color_features):
        self.id = id
        self.embeddings = embeddings
        self.environment_vectors = environment_vectors
        self.color_features = color_features
        self.centroid = torch.mean(embeddings, dim=0)
        self.environment_centroid = torch.mean(environment_vectors, dim=0)
        self.color_centroid = torch.mean(color_features, dim=0)

    def score(self, other):
        # Environment-weighted scoring
        env_score = torch.nn.functional.cosine_similarity(
            self.environment_centroid, other.environment_centroid
        ).item()
        
        color_score = torch.nn.functional.cosine_similarity(
            self.color_centroid, other.color_centroid
        ).item()
        
        global_score = torch.nn.functional.cosine_similarity(
            self.centroid, other.centroid
        ).item()
        
        # Final score: 50% environment + 30% color + 20% global
        return 0.5 * env_score + 0.3 * color_score + 0.2 * global_score
EOF

# 📜 Update recognizer.py (v3.1 logic)
echo "Updating recognizer.py for v3.1..."
cat > fingerprint_v31/recognizer.py <<EOF
import os
import torch
from fingerprint import Fingerprint
from utils import load_fingerprint_database

class Recognizer:
    def __init__(self, db_path="fingerprint_v31/database.json"):
        self.db = load_fingerprint_database(db_path)
        self.fingerprint_cache = {}

    def recognize(self, image_path, threshold=0.6):
        if image_path in self.fingerprint_cache:
            return self.fingerprint_cache[image_path]
        
        # Create new fingerprint
        embedder = Embedder()
        fingerprint = embedder.get_embeddings(image_path)
        
        # Compare with database
        results = []
        for fid, fp in self.db.items():
            score = fingerprint.score(fp)
            results.append({
                "id": fid,
                "score": score,
                "environment_similarity": fingerprint.environment_similarity(fp),
                "color_similarity": fingerprint.color_similarity(fp),
                "global_similarity": fingerprint.global_similarity(fp)
            })
        
        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Find best match
        best = results[0]
        best["best_id"] = best["id"]
        best["candidates"] = results
        
        self.fingerprint_cache[image_path] = best
        return best
EOF

# 📜 Update scene_analyzer.py (v3.1 logic)
echo "Updating scene_analyzer.py for v3.1..."
cat > fingerprint_v31/scene_analyzer.py <<EOF
import os
import torch
from recognizer import Recognizer
from utils import analyze_scene

class SceneAnalyzer:
    def __init__(self, db_path="fingerprint_v31/database.json"):
        self.recognizer = Recognizer(db_path)
    
    def analyze(self, image_path):
        result = self.recognizer.recognize(image_path)
        return analyze_scene(result)
EOF

# 📜 Update cli.py (v3.1 logic)
echo "Updating cli.py for v3.1..."
cat > fingerprint_v31/cli.py <<EOF
import os
import argparse
from fingerprint import Fingerprint
from recognizer import Recognizer
from scene_analyzer import SceneAnalyzer
from utils import save_fingerprint, load_fingerprint_database

def main():
    parser = argparse.ArgumentParser(description="Scene Fingerprinting System")
    parser.add_argument("command", choices=["create", "recognize", "analyze"], help="Command to execute")
    parser.add_argument("--file", required=True, help="Image file path")
    parser.add_argument("--id", help="Fingerprint ID")
    parser.add_argument("--db", default="fingerprint_v31/database.json", help="Database path")
    
    args = parser.parse_args()
    
    if args.command == "create":
        embedder = Embedder()
        fingerprint = embedder.get_embeddings(args.file)
        save_fingerprint(args.id, fingerprint)
        print(f"Saved fingerprint {args.id}")
    
    elif args.command == "recognize":
        recognizer = Recognizer(args.db)
        result = recognizer.recognize(args.file)
        print(f"Best match: {result['best_id']} (Score: {result['score']})")
        for candidate in result['candidates']:
            print(f"  {candidate['id']} - {candidate['score']}")
    
    elif args.command == "analyze":
        analyzer = SceneAnalyzer(args.db)
        result = analyzer.analyze(args.file)
        print(f"Scene analysis for {args.file}:")
        for key, value in result.items():
            print(f"  {key}: {value}")

if __name__ == "__main__":
    main()
EOF

# 📁 Move files to v3.1
echo "Moving files to v3.1 directory..."
mv fingerprint_v31/* models_v31/* logs_v31/* fingerprint_v31/
rm -rf models_v31 logs_v31

# 🧠 Final check
echo "✅ Upgrade to v3.1 completed!"
echo "New files are in fingerprint_v31/"
echo "To use, run:"
echo "uv run scene-fingerprint create --file data/input/new/001.JPG --id 78_v31"
echo "uv run scene-fingerprint recognize --file data/input/new/001.JPG"
```

---

### 📌 Как это работает

1. **Бэкап** старой версии v3
2. **Создание** отдельной папки `fingerprint_v31`
3. **Обновление** логики:
   - **Environment-weighted scoring** (50% окружение + 30% цвет + 20% глобальный)
   - **Новые признаки**: окружение, цвет, пространственная структура
   - **Совместимость**: сохраняет старые команды CLI
4. **Тестирование**:
   ```bash
   uv run scene-fingerprint create --file data/input/new/001.JPG --id 78_v31
   uv run scene-fingerprint recognize --file data/input/new/001.JPG
   ```

---

### 📌 Примечания

- Скрипт **не ломает** существующие данные
- Новые фингерпринты (78_v31, 79_v31, 80_v31) будут **совместимы** с предыдущими версиями
- Для обучения LoRA/моделирования окружения можно использовать **после** этого шага

Если хочешь, я могу добавить **автоматическую генерацию новых фингерпринтов** для 79/80/81 в этот скрипт.