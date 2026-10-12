### 🧹 **Очистка `data/output` и `data/subfingerprints_exp`**

#### 1. **Удаляем JPG в `data/output`**
```bash
cd ~/projects/scene_fingerprint_mvp_v02

# Удаляем JPG/JPEG
find data/output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -delete

# Проверяем, сколько осталось JPG
echo "Осталось JPG:"
find data/output -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) | wc -l

# Проверяем размер `data/output`
echo "Размер data/output:"
du -sh data/output
```

#### 2. **Удаляем JPG в `data/subfingerprints_exp`**
```bash
find data/subfingerprints_exp -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -delete
```

#### 3. **Удаляем старые экспериментальные файлы**
```bash
# Удаляем ненужные экспериментальные файлы (если они не нужны)
rm -rf data/subfingerprints_exp/old_experiments
```

#### 4. **Проверяем итоговый объем**
```bash
du -sh data
du -sh data/output
du -sh data/subfingerprints_exp
```

---

### ✅ **Итог**
- **`data/input` и `data/fingerprints`** — **не трогаем** (важные рабочие данные).
- **`data/output`** — **очищаем от JPG**, оставляем JSON/CSV.
- **`data/subfingerprints_exp`** — **удаляем JPG**, оставляем экспериментальные данные (если они нужны).

Если всё верно, я выполню команды вручную. Проверь, пожалуйста, что всё выше указанное подходит.