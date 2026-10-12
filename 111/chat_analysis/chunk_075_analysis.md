```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "=== TEST PHOTOS ==="
find data/input/test -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  -printf "%f\n" | sort | head -20

echo
echo "=== COUNT ==="
find data/input/test -maxdepth 1 -type f \
  \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
  | wc -l

echo
echo "=== CURRENT PHOTO MODULE ==="
sed -n '1,280p' app/web/components/photos.py
```