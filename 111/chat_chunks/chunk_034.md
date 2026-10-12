## СЕССИЯ: Версии recognizer.py

**Создано:** 2026-08-15 02:51:35
**Обновлено:** 2026-08-19 17:08:05
**Ссылка:** [https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81](https://chatgpt.com/g/g-p-6a85b8a643948191a6d0fa3b107f16c2/c/6a7faa06-2e74-83ea-948a-55c01b4aff81)

---

### 👤 **User** — 2026-08-15 03:45:14

alexice@NEURO:~/Desktop$ cd ~/projects/scene_fingerprint_mvp_v02

for n in $(seq 78 95); do
    echo
    echo "============================================================"
    echo "CREATING ${n}_v33"
    echo "============================================================"

    rm -rf "data/fingerprints/${n}_v33"

    uv run scene-fingerprint create \
        "${n}_v33" \
        "data/input/${n}" || exit 1
done

============================================================
CREATING 78_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9124.28it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '78_v33' from 81 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/78_v33
[Fingerprint v3.3] global=(81, 768)
[Fingerprint v3.3] environment=(81, 640)
[Fingerprint v3.3] color=(81, 48)
[Fingerprint v3.3] spatial=(81, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "78_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 81,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "78_001.JPG",
    "78_002.JPG",
    "78_003.JPG",
    "78_004.JPG",
    "78_005.JPG",
    "78_006.JPG",
    "78_007.JPG",
    "78_008.JPG",
    "78_009.JPG",
    "78_010.JPG",
    "78_011.JPG",
    "78_012.JPG",
    "78_013.JPG",
    "78_014.JPG",
    "78_015.JPG",
    "78_016.JPG",
    "78_017.JPG",
    "78_018.JPG",
    "78_019.JPG",
    "78_020.JPG",
    "78_021.JPG",
    "78_022.JPG",
    "78_023.JPG",
    "78_024.JPG",
    "78_025.JPG",
    "78_026.JPG",
    "78_027.JPG",
    "78_028.JPG",
    "78_029.JPG",
    "78_030.JPG",
    "78_031.JPG",
    "78_032.JPG",
    "78_033.JPG",
    "78_034.JPG",
    "78_035.JPG",
    "78_036.JPG",
    "78_037.JPG",
    "78_038.JPG",
    "78_039.JPG",
    "78_040.JPG",
    "78_041.JPG",
    "78_042.JPG",
    "78_043.JPG",
    "78_044.JPG",
    "78_045.JPG",
    "78_046.JPG",
    "78_047.JPG",
    "78_048.JPG",
    "78_049.JPG",
    "78_050.JPG",
    "78_051.JPG",
    "78_052.JPG",
    "78_053.JPG",
    "78_054.JPG",
    "78_055.JPG",
    "78_056.JPG",
    "78_057.JPG",
    "78_058.JPG",
    "78_059.JPG",
    "78_060.JPG",
    "78_061.JPG",
    "78_062.JPG",
    "78_063.JPG",
    "78_064.JPG",
    "78_065.JPG",
    "78_066.JPG",
    "78_067.JPG",
    "78_068.JPG",
    "78_069.JPG",
    "78_070.JPG",
    "78_071.JPG",
    "78_072.JPG",
    "78_073.JPG",
    "78_074.JPG",
    "78_075.JPG",
    "78_076.JPG",
    "78_077.JPG",
    "78_078.JPG",
    "78_079.JPG",
    "78_080.JPG",
    "78_081.JPG"
  ]
}

============================================================
CREATING 79_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9658.01it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '79_v33' from 65 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/79_v33
[Fingerprint v3.3] global=(65, 768)
[Fingerprint v3.3] environment=(65, 640)
[Fingerprint v3.3] color=(65, 48)
[Fingerprint v3.3] spatial=(65, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "79_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 65,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "79_001.JPG",
    "79_002.JPG",
    "79_003.JPG",
    "79_004.JPG",
    "79_005.JPG",
    "79_006.JPG",
    "79_007.JPG",
    "79_008.JPG",
    "79_009.JPG",
    "79_010.JPG",
    "79_011.JPG",
    "79_012.JPG",
    "79_013.JPG",
    "79_014.JPG",
    "79_015.JPG",
    "79_016.JPG",
    "79_017.JPG",
    "79_018.JPG",
    "79_019.JPG",
    "79_020.JPG",
    "79_021.JPG",
    "79_022.JPG",
    "79_023.JPG",
    "79_024.JPG",
    "79_025.JPG",
    "79_026.JPG",
    "79_027.JPG",
    "79_028.JPG",
    "79_029.JPG",
    "79_030.JPG",
    "79_031.JPG",
    "79_032.JPG",
    "79_033.JPG",
    "79_034.JPG",
    "79_035.JPG",
    "79_036.JPG",
    "79_037.JPG",
    "79_038.JPG",
    "79_039.JPG",
    "79_040.JPG",
    "79_041.JPG",
    "79_042.JPG",
    "79_043.JPG",
    "79_044.JPG",
    "79_045.JPG",
    "79_046.JPG",
    "79_047.JPG",
    "79_048.JPG",
    "79_049.JPG",
    "79_050.JPG",
    "79_051.JPG",
    "79_052.JPG",
    "79_053.JPG",
    "79_054.JPG",
    "79_055.JPG",
    "79_056.JPG",
    "79_057.JPG",
    "79_058.JPG",
    "79_059.JPG",
    "79_060.JPG",
    "79_061.JPG",
    "79_062.JPG",
    "79_063.JPG",
    "79_064.JPG",
    "79_065.JPG"
  ]
}

============================================================
CREATING 80_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9101.99it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '80_v33' from 37 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/80_v33
[Fingerprint v3.3] global=(37, 768)
[Fingerprint v3.3] environment=(37, 640)
[Fingerprint v3.3] color=(37, 48)
[Fingerprint v3.3] spatial=(37, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "80_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 37,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "80_001.JPG",
    "80_002.JPG",
    "80_003.JPG",
    "80_004.JPG",
    "80_005.JPG",
    "80_006.JPG",
    "80_007.JPG",
    "80_008.JPG",
    "80_009.JPG",
    "80_010.JPG",
    "80_011.JPG",
    "80_012.JPG",
    "80_013.JPG",
    "80_014.JPG",
    "80_015.JPG",
    "80_016.JPG",
    "80_017.JPG",
    "80_018.JPG",
    "80_019.JPG",
    "80_020.JPG",
    "80_021.JPG",
    "80_022.JPG",
    "80_023.JPG",
    "80_024.JPG",
    "80_025.JPG",
    "80_026.JPG",
    "80_027.JPG",
    "80_028.JPG",
    "80_029.JPG",
    "80_030.JPG",
    "80_031.JPG",
    "80_032.JPG",
    "80_033.JPG",
    "80_034.JPG",
    "80_035.JPG",
    "80_036.JPG",
    "80_037.JPG"
  ]
}

============================================================
CREATING 81_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9001.78it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '81_v33' from 65 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/81_v33
[Fingerprint v3.3] global=(65, 768)
[Fingerprint v3.3] environment=(65, 640)
[Fingerprint v3.3] color=(65, 48)
[Fingerprint v3.3] spatial=(65, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "81_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 65,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "81_001.JPG",
    "81_002.JPG",
    "81_003.JPG",
    "81_004.JPG",
    "81_005.JPG",
    "81_006.JPG",
    "81_007.JPG",
    "81_008.JPG",
    "81_009.JPG",
    "81_010.JPG",
    "81_011.JPG",
    "81_012.JPG",
    "81_013.JPG",
    "81_014.JPG",
    "81_015.JPG",
    "81_016.JPG",
    "81_017.JPG",
    "81_018.JPG",
    "81_019.JPG",
    "81_020.JPG",
    "81_021.JPG",
    "81_022.JPG",
    "81_023.JPG",
    "81_024.JPG",
    "81_025.JPG",
    "81_026.JPG",
    "81_027.JPG",
    "81_028.JPG",
    "81_029.JPG",
    "81_030.JPG",
    "81_031.JPG",
    "81_032.JPG",
    "81_033.JPG",
    "81_034.JPG",
    "81_035.JPG",
    "81_036.JPG",
    "81_037.JPG",
    "81_038.JPG",
    "81_039.JPG",
    "81_040.JPG",
    "81_041.JPG",
    "81_042.JPG",
    "81_043.JPG",
    "81_044.JPG",
    "81_045.JPG",
    "81_046.JPG",
    "81_047.JPG",
    "81_048.JPG",
    "81_049.JPG",
    "81_050.JPG",
    "81_051.JPG",
    "81_052.JPG",
    "81_053.JPG",
    "81_054.JPG",
    "81_055.JPG",
    "81_056.JPG",
    "81_057.JPG",
    "81_058.JPG",
    "81_059.JPG",
    "81_060.JPG",
    "81_061.JPG",
    "81_062.JPG",
    "81_063.JPG",
    "81_064.JPG",
    "81_065.JPG"
  ]
}

============================================================
CREATING 82_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8978.28it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '82_v33' from 67 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/82_v33
[Fingerprint v3.3] global=(67, 768)
[Fingerprint v3.3] environment=(67, 640)
[Fingerprint v3.3] color=(67, 48)
[Fingerprint v3.3] spatial=(67, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "82_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 67,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "82_001.JPG",
    "82_002.JPG",
    "82_003.JPG",
    "82_004.JPG",
    "82_005.JPG",
    "82_006.JPG",
    "82_007.JPG",
    "82_008.JPG",
    "82_009.JPG",
    "82_010.JPG",
    "82_011.JPG",
    "82_012.JPG",
    "82_013.JPG",
    "82_014.JPG",
    "82_015.JPG",
    "82_016.JPG",
    "82_017.JPG",
    "82_018.JPG",
    "82_019.JPG",
    "82_020.JPG",
    "82_021.JPG",
    "82_022.JPG",
    "82_023.JPG",
    "82_024.JPG",
    "82_025.JPG",
    "82_026.JPG",
    "82_027.JPG",
    "82_028.JPG",
    "82_029.JPG",
    "82_030.JPG",
    "82_031.JPG",
    "82_032.JPG",
    "82_033.JPG",
    "82_034.JPG",
    "82_035.JPG",
    "82_036.JPG",
    "82_037.JPG",
    "82_038.JPG",
    "82_039.JPG",
    "82_040.JPG",
    "82_041.JPG",
    "82_042.JPG",
    "82_043.JPG",
    "82_044.JPG",
    "82_045.JPG",
    "82_046.JPG",
    "82_047.JPG",
    "82_048.JPG",
    "82_049.JPG",
    "82_050.JPG",
    "82_051.JPG",
    "82_052.JPG",
    "82_053.JPG",
    "82_054.JPG",
    "82_055.JPG",
    "82_056.JPG",
    "82_057.JPG",
    "82_058.JPG",
    "82_059.JPG",
    "82_060.JPG",
    "82_061.JPG",
    "82_062.JPG",
    "82_063.JPG",
    "82_064.JPG",
    "82_065.JPG",
    "82_066.JPG",
    "82_067.JPG"
  ]
}

============================================================
CREATING 83_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8708.28it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '83_v33' from 68 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/83_v33
[Fingerprint v3.3] global=(68, 768)
[Fingerprint v3.3] environment=(68, 640)
[Fingerprint v3.3] color=(68, 48)
[Fingerprint v3.3] spatial=(68, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "83_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 68,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "83_001.JPG",
    "83_002.JPG",
    "83_003.JPG",
    "83_004.JPG",
    "83_005.JPG",
    "83_006.JPG",
    "83_007.JPG",
    "83_008.JPG",
    "83_009.JPG",
    "83_010.JPG",
    "83_011.JPG",
    "83_012.JPG",
    "83_013.JPG",
    "83_014.JPG",
    "83_015.JPG",
    "83_016.JPG",
    "83_017.JPG",
    "83_018.JPG",
    "83_019.JPG",
    "83_020.JPG",
    "83_021.JPG",
    "83_022.JPG",
    "83_023.JPG",
    "83_024.JPG",
    "83_025.JPG",
    "83_026.JPG",
    "83_027.JPG",
    "83_028.JPG",
    "83_029.JPG",
    "83_030.JPG",
    "83_031.JPG",
    "83_032.JPG",
    "83_033.JPG",
    "83_034.JPG",
    "83_035.JPG",
    "83_036.JPG",
    "83_037.JPG",
    "83_038.JPG",
    "83_039.JPG",
    "83_040.JPG",
    "83_041.JPG",
    "83_042.JPG",
    "83_043.JPG",
    "83_044.JPG",
    "83_045.JPG",
    "83_046.JPG",
    "83_047.JPG",
    "83_048.JPG",
    "83_049.JPG",
    "83_050.JPG",
    "83_051.JPG",
    "83_052.JPG",
    "83_053.JPG",
    "83_054.JPG",
    "83_055.JPG",
    "83_056.JPG",
    "83_057.JPG",
    "83_058.JPG",
    "83_059.JPG",
    "83_060.JPG",
    "83_061.JPG",
    "83_062.JPG",
    "83_063.JPG",
    "83_064.JPG",
    "83_065.JPG",
    "83_066.JPG",
    "83_067.JPG",
    "83_068.JPG"
  ]
}

============================================================
CREATING 84_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9327.09it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '84_v33' from 54 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/84_v33
[Fingerprint v3.3] global=(54, 768)
[Fingerprint v3.3] environment=(54, 640)
[Fingerprint v3.3] color=(54, 48)
[Fingerprint v3.3] spatial=(54, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "84_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 54,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "84_001.JPG",
    "84_002.JPG",
    "84_003.JPG",
    "84_004.JPG",
    "84_005.JPG",
    "84_006.JPG",
    "84_007.JPG",
    "84_008.JPG",
    "84_009.JPG",
    "84_010.JPG",
    "84_011.JPG",
    "84_012.JPG",
    "84_013.JPG",
    "84_014.JPG",
    "84_015.JPG",
    "84_016.JPG",
    "84_017.JPG",
    "84_018.JPG",
    "84_019.JPG",
    "84_020.JPG",
    "84_021.JPG",
    "84_022.JPG",
    "84_023.JPG",
    "84_024.JPG",
    "84_025.JPG",
    "84_026.JPG",
    "84_027.JPG",
    "84_028.JPG",
    "84_029.JPG",
    "84_030.JPG",
    "84_031.JPG",
    "84_032.JPG",
    "84_033.JPG",
    "84_034.JPG",
    "84_035.JPG",
    "84_036.JPG",
    "84_037.JPG",
    "84_038.JPG",
    "84_039.JPG",
    "84_040.JPG",
    "84_041.JPG",
    "84_042.JPG",
    "84_043.JPG",
    "84_044.JPG",
    "84_045.JPG",
    "84_046.JPG",
    "84_047.JPG",
    "84_048.JPG",
    "84_049.JPG",
    "84_050.JPG",
    "84_051.JPG",
    "84_052.JPG",
    "84_053.JPG",
    "84_054.JPG"
  ]
}

============================================================
CREATING 85_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8704.30it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '85_v33' from 58 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/85_v33
[Fingerprint v3.3] global=(58, 768)
[Fingerprint v3.3] environment=(58, 640)
[Fingerprint v3.3] color=(58, 48)
[Fingerprint v3.3] spatial=(58, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "85_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 58,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "85_001.JPG",
    "85_002.JPG",
    "85_003.JPG",
    "85_004.JPG",
    "85_005.JPG",
    "85_006.JPG",
    "85_007.JPG",
    "85_008.JPG",
    "85_009.JPG",
    "85_010.JPG",
    "85_011.JPG",
    "85_012.JPG",
    "85_013.JPG",
    "85_014.JPG",
    "85_015.JPG",
    "85_016.JPG",
    "85_017.JPG",
    "85_018.JPG",
    "85_019.JPG",
    "85_020.JPG",
    "85_021.JPG",
    "85_022.JPG",
    "85_023.JPG",
    "85_024.JPG",
    "85_025.JPG",
    "85_026.JPG",
    "85_027.JPG",
    "85_028.JPG",
    "85_029.JPG",
    "85_030.JPG",
    "85_031.JPG",
    "85_032.JPG",
    "85_033.JPG",
    "85_034.JPG",
    "85_035.JPG",
    "85_036.JPG",
    "85_037.JPG",
    "85_038.JPG",
    "85_039.JPG",
    "85_040.JPG",
    "85_041.JPG",
    "85_042.JPG",
    "85_043.JPG",
    "85_044.JPG",
    "85_045.JPG",
    "85_046.JPG",
    "85_047.JPG",
    "85_048.JPG",
    "85_049.JPG",
    "85_050.JPG",
    "85_051.JPG",
    "85_052.JPG",
    "85_053.JPG",
    "85_054.JPG",
    "85_055.JPG",
    "85_056.JPG",
    "85_057.JPG",
    "85_058.JPG"
  ]
}

============================================================
CREATING 86_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9303.25it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '86_v33' from 58 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/86_v33
[Fingerprint v3.3] global=(58, 768)
[Fingerprint v3.3] environment=(58, 640)
[Fingerprint v3.3] color=(58, 48)
[Fingerprint v3.3] spatial=(58, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "86_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 58,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "86_001.JPG",
    "86_002.JPG",
    "86_003.JPG",
    "86_004.JPG",
    "86_005.JPG",
    "86_006.JPG",
    "86_007.JPG",
    "86_008.JPG",
    "86_009.JPG",
    "86_010.JPG",
    "86_011.JPG",
    "86_012.JPG",
    "86_013.JPG",
    "86_014.JPG",
    "86_015.JPG",
    "86_016.JPG",
    "86_017.JPG",
    "86_018.JPG",
    "86_019.JPG",
    "86_020.JPG",
    "86_021.JPG",
    "86_022.JPG",
    "86_023.JPG",
    "86_024.JPG",
    "86_025.JPG",
    "86_026.JPG",
    "86_027.JPG",
    "86_028.JPG",
    "86_029.JPG",
    "86_030.JPG",
    "86_031.JPG",
    "86_032.JPG",
    "86_033.JPG",
    "86_034.JPG",
    "86_035.JPG",
    "86_036.JPG",
    "86_037.JPG",
    "86_038.JPG",
    "86_039.JPG",
    "86_040.JPG",
    "86_041.JPG",
    "86_042.JPG",
    "86_043.JPG",
    "86_044.JPG",
    "86_045.JPG",
    "86_046.JPG",
    "86_047.JPG",
    "86_048.JPG",
    "86_049.JPG",
    "86_050.JPG",
    "86_051.JPG",
    "86_052.JPG",
    "86_053.JPG",
    "86_054.JPG",
    "86_055.JPG",
    "86_056.JPG",
    "86_057.JPG",
    "86_058.JPG"
  ]
}

============================================================
CREATING 87_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8871.82it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '87_v33' from 50 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/87_v33
[Fingerprint v3.3] global=(50, 768)
[Fingerprint v3.3] environment=(50, 640)
[Fingerprint v3.3] color=(50, 48)
[Fingerprint v3.3] spatial=(50, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "87_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 50,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "87_001.JPG",
    "87_002.JPG",
    "87_003.JPG",
    "87_004.JPG",
    "87_005.JPG",
    "87_006.JPG",
    "87_007.JPG",
    "87_008.JPG",
    "87_009.JPG",
    "87_010.JPG",
    "87_011.JPG",
    "87_012.JPG",
    "87_013.JPG",
    "87_014.JPG",
    "87_015.JPG",
    "87_016.JPG",
    "87_017.JPG",
    "87_018.JPG",
    "87_019.JPG",
    "87_020.JPG",
    "87_021.JPG",
    "87_022.JPG",
    "87_023.JPG",
    "87_024.JPG",
    "87_025.JPG",
    "87_026.JPG",
    "87_027.JPG",
    "87_028.JPG",
    "87_029.JPG",
    "87_030.JPG",
    "87_031.JPG",
    "87_032.JPG",
    "87_033.JPG",
    "87_034.JPG",
    "87_035.JPG",
    "87_036.JPG",
    "87_037.JPG",
    "87_038.JPG",
    "87_039.JPG",
    "87_040.JPG",
    "87_041.JPG",
    "87_042.JPG",
    "87_043.JPG",
    "87_044.JPG",
    "87_045.JPG",
    "87_046.JPG",
    "87_047.JPG",
    "87_048.JPG",
    "87_049.JPG",
    "87_050.JPG"
  ]
}

============================================================
CREATING 88_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9232.99it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '88_v33' from 54 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/88_v33
[Fingerprint v3.3] global=(54, 768)
[Fingerprint v3.3] environment=(54, 640)
[Fingerprint v3.3] color=(54, 48)
[Fingerprint v3.3] spatial=(54, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "88_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 54,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "88_001.JPG",
    "88_002.JPG",
    "88_003.JPG",
    "88_004.JPG",
    "88_005.JPG",
    "88_006.JPG",
    "88_007.JPG",
    "88_008.JPG",
    "88_009.JPG",
    "88_010.JPG",
    "88_011.JPG",
    "88_012.JPG",
    "88_013.JPG",
    "88_014.JPG",
    "88_015.JPG",
    "88_016.JPG",
    "88_017.JPG",
    "88_018.JPG",
    "88_019.JPG",
    "88_020.JPG",
    "88_021.JPG",
    "88_022.JPG",
    "88_023.JPG",
    "88_024.JPG",
    "88_025.JPG",
    "88_026.JPG",
    "88_027.JPG",
    "88_028.JPG",
    "88_029.JPG",
    "88_030.JPG",
    "88_031.JPG",
    "88_032.JPG",
    "88_033.JPG",
    "88_034.JPG",
    "88_035.JPG",
    "88_036.JPG",
    "88_037.JPG",
    "88_038.JPG",
    "88_039.JPG",
    "88_040.JPG",
    "88_041.JPG",
    "88_042.JPG",
    "88_043.JPG",
    "88_044.JPG",
    "88_045.JPG",
    "88_046.JPG",
    "88_047.JPG",
    "88_048.JPG",
    "88_049.JPG",
    "88_050.JPG",
    "88_051.JPG",
    "88_052.JPG",
    "88_053.JPG",
    "88_054.JPG"
  ]
}

============================================================
CREATING 89_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9091.64it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '89_v33' from 64 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/89_v33
[Fingerprint v3.3] global=(64, 768)
[Fingerprint v3.3] environment=(64, 640)
[Fingerprint v3.3] color=(64, 48)
[Fingerprint v3.3] spatial=(64, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "89_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 64,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "89_001.JPG",
    "89_002.JPG",
    "89_003.JPG",
    "89_004.JPG",
    "89_005.JPG",
    "89_006.JPG",
    "89_007.JPG",
    "89_008.JPG",
    "89_009.JPG",
    "89_010.JPG",
    "89_011.JPG",
    "89_012.JPG",
    "89_013.JPG",
    "89_014.JPG",
    "89_015.JPG",
    "89_016.JPG",
    "89_017.JPG",
    "89_018.JPG",
    "89_019.JPG",
    "89_020.JPG",
    "89_021.JPG",
    "89_022.JPG",
    "89_023.JPG",
    "89_024.JPG",
    "89_025.JPG",
    "89_026.JPG",
    "89_027.JPG",
    "89_028.JPG",
    "89_029.JPG",
    "89_030.JPG",
    "89_031.JPG",
    "89_032.JPG",
    "89_033.JPG",
    "89_034.JPG",
    "89_035.JPG",
    "89_036.JPG",
    "89_037.JPG",
    "89_038.JPG",
    "89_039.JPG",
    "89_040.JPG",
    "89_041.JPG",
    "89_042.JPG",
    "89_043.JPG",
    "89_044.JPG",
    "89_045.JPG",
    "89_046.JPG",
    "89_047.JPG",
    "89_048.JPG",
    "89_049.JPG",
    "89_050.JPG",
    "89_051.JPG",
    "89_052.JPG",
    "89_053.JPG",
    "89_054.JPG",
    "89_055.JPG",
    "89_056.JPG",
    "89_057.JPG",
    "89_058.JPG",
    "89_059.JPG",
    "89_060.JPG",
    "89_061.JPG",
    "89_062.JPG",
    "89_063.JPG",
    "89_064.JPG"
  ]
}

============================================================
CREATING 90_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9019.23it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '90_v33' from 19 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/90_v33
[Fingerprint v3.3] global=(19, 768)
[Fingerprint v3.3] environment=(19, 640)
[Fingerprint v3.3] color=(19, 48)
[Fingerprint v3.3] spatial=(19, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "90_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 19,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "90_001.jpg",
    "90_002.jpg",
    "90_003.jpg",
    "90_004.JPG",
    "90_005.JPG",
    "90_006.JPG",
    "90_007.JPG",
    "90_008.JPG",
    "90_009.JPG",
    "90_010.JPG",
    "90_011.JPG",
    "90_012.JPG",
    "90_013.JPG",
    "90_014.JPG",
    "90_015.JPG",
    "90_016.JPG",
    "90_017.JPG",
    "90_018.JPG",
    "90_019.JPG"
  ]
}

============================================================
CREATING 91_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9556.37it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '91_v33' from 41 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/91_v33
[Fingerprint v3.3] global=(41, 768)
[Fingerprint v3.3] environment=(41, 640)
[Fingerprint v3.3] color=(41, 48)
[Fingerprint v3.3] spatial=(41, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "91_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 41,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "91_001.JPG",
    "91_002.JPG",
    "91_003.JPG",
    "91_004.JPG",
    "91_005.JPG",
    "91_006.JPG",
    "91_007.JPG",
    "91_008.JPG",
    "91_009.JPG",
    "91_010.JPG",
    "91_011.JPG",
    "91_012.JPG",
    "91_013.JPG",
    "91_014.JPG",
    "91_015.JPG",
    "91_016.JPG",
    "91_017.JPG",
    "91_018.JPG",
    "91_019.JPG",
    "91_020.JPG",
    "91_021.JPG",
    "91_022.JPG",
    "91_023.JPG",
    "91_024.JPG",
    "91_025.JPG",
    "91_026.JPG",
    "91_027.JPG",
    "91_028.JPG",
    "91_029.JPG",
    "91_030.JPG",
    "91_031.JPG",
    "91_032.JPG",
    "91_033.JPG",
    "91_034.JPG",
    "91_035.JPG",
    "91_036.JPG",
    "91_037.JPG",
    "91_038.JPG",
    "91_039.JPG",
    "91_040.JPG",
    "91_041.JPG"
  ]
}

============================================================
CREATING 92_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8988.80it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '92_v33' from 57 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/92_v33
[Fingerprint v3.3] global=(57, 768)
[Fingerprint v3.3] environment=(57, 640)
[Fingerprint v3.3] color=(57, 48)
[Fingerprint v3.3] spatial=(57, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "92_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 57,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "92_001.JPG",
    "92_002.JPG",
    "92_003.JPG",
    "92_004.JPG",
    "92_005.JPG",
    "92_006.JPG",
    "92_007.JPG",
    "92_008.JPG",
    "92_009.JPG",
    "92_010.JPG",
    "92_011.JPG",
    "92_012.JPG",
    "92_013.JPG",
    "92_014.JPG",
    "92_015.JPG",
    "92_016.JPG",
    "92_017.JPG",
    "92_018.JPG",
    "92_019.JPG",
    "92_020.JPG",
    "92_021.JPG",
    "92_022.JPG",
    "92_023.JPG",
    "92_024.JPG",
    "92_025.JPG",
    "92_026.JPG",
    "92_027.JPG",
    "92_028.JPG",
    "92_029.JPG",
    "92_030.JPG",
    "92_031.JPG",
    "92_032.JPG",
    "92_033.JPG",
    "92_034.JPG",
    "92_035.JPG",
    "92_036.JPG",
    "92_037.JPG",
    "92_038.JPG",
    "92_039.JPG",
    "92_040.JPG",
    "92_041.JPG",
    "92_042.JPG",
    "92_043.JPG",
    "92_044.JPG",
    "92_045.JPG",
    "92_046.JPG",
    "92_047.JPG",
    "92_048.JPG",
    "92_049.JPG",
    "92_050.JPG",
    "92_051.JPG",
    "92_052.JPG",
    "92_053.JPG",
    "92_054.JPG",
    "92_055.JPG",
    "92_056.JPG",
    "92_057.JPG"
  ]
}

============================================================
CREATING 93_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|████████████████████| 223/223 [00:00<00:00, 10076.05it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '93_v33' from 51 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/93_v33
[Fingerprint v3.3] global=(51, 768)
[Fingerprint v3.3] environment=(51, 640)
[Fingerprint v3.3] color=(51, 48)
[Fingerprint v3.3] spatial=(51, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "93_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 51,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "93_001.JPG",
    "93_002.JPG",
    "93_003.JPG",
    "93_004.JPG",
    "93_005.JPG",
    "93_006.JPG",
    "93_007.JPG",
    "93_008.JPG",
    "93_009.JPG",
    "93_010.JPG",
    "93_011.JPG",
    "93_012.JPG",
    "93_013.JPG",
    "93_014.JPG",
    "93_015.JPG",
    "93_016.JPG",
    "93_017.JPG",
    "93_018.JPG",
    "93_019.JPG",
    "93_020.JPG",
    "93_021.JPG",
    "93_022.JPG",
    "93_023.JPG",
    "93_024.JPG",
    "93_025.JPG",
    "93_026.JPG",
    "93_027.JPG",
    "93_028.JPG",
    "93_029.JPG",
    "93_030.JPG",
    "93_031.JPG",
    "93_032.JPG",
    "93_033.JPG",
    "93_034.JPG",
    "93_035.JPG",
    "93_036.JPG",
    "93_037.JPG",
    "93_038.JPG",
    "93_039.JPG",
    "93_040.JPG",
    "93_041.JPG",
    "93_042.JPG",
    "93_043.JPG",
    "93_044.JPG",
    "93_045.JPG",
    "93_046.JPG",
    "93_047.JPG",
    "93_048.JPG",
    "93_049.JPG",
    "93_050.JPG",
    "93_051.JPG"
  ]
}

============================================================
CREATING 94_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 8334.64it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '94_v33' from 67 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/94_v33
[Fingerprint v3.3] global=(67, 768)
[Fingerprint v3.3] environment=(67, 640)
[Fingerprint v3.3] color=(67, 48)
[Fingerprint v3.3] spatial=(67, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "94_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 67,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "94_001.JPG",
    "94_002.JPG",
    "94_003.JPG",
    "94_004.JPG",
    "94_005.JPG",
    "94_006.JPG",
    "94_007.JPG",
    "94_008.JPG",
    "94_009.JPG",
    "94_010.JPG",
    "94_011.JPG",
    "94_012.JPG",
    "94_013.JPG",
    "94_014.JPG",
    "94_015.JPG",
    "94_016.JPG",
    "94_017.JPG",
    "94_018.JPG",
    "94_019.JPG",
    "94_020.JPG",
    "94_021.JPG",
    "94_022.JPG",
    "94_023.JPG",
    "94_024.JPG",
    "94_025.JPG",
    "94_026.JPG",
    "94_027.JPG",
    "94_028.JPG",
    "94_029.JPG",
    "94_030.JPG",
    "94_031.JPG",
    "94_032.JPG",
    "94_033.JPG",
    "94_034.JPG",
    "94_035.JPG",
    "94_036.JPG",
    "94_037.JPG",
    "94_038.JPG",
    "94_039.JPG",
    "94_040.JPG",
    "94_041.JPG",
    "94_042.JPG",
    "94_043.JPG",
    "94_044.JPG",
    "94_045.JPG",
    "94_046.JPG",
    "94_047.JPG",
    "94_048.JPG",
    "94_049.JPG",
    "94_050.JPG",
    "94_051.JPG",
    "94_052.JPG",
    "94_053.JPG",
    "94_054.JPG",
    "94_055.JPG",
    "94_056.JPG",
    "94_057.JPG",
    "94_058.JPG",
    "94_059.JPG",
    "94_060.JPG",
    "94_061.JPG",
    "94_062.JPG",
    "94_063.JPG",
    "94_064.JPG",
    "94_065.JPG",
    "94_066.JPG",
    "94_067.JPG"
  ]
}

============================================================
CREATING 95_v33
============================================================
[SceneEmbedder] device=cuda
[SceneEmbedder] GPU=NVIDIA GeForce RTX 3060
[SceneEmbedder] VRAM=11.6 GB
[SceneEmbedder] Loading DINOv2: facebook/dinov2-base
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|█████████████████████| 223/223 [00:00<00:00, 9080.78it/s]
[SceneEmbedder] embedding dimension=768
[SceneEmbedder] patch extraction=DISABLED (compact)
[SceneEmbedder] Ready.
[Fingerprint v3.3] Creating '95_v33' from 86 images
[Fingerprint v3.3] Building compact descriptors...
[Fingerprint v3.3] CPU workers=6
[Fingerprint v3.3] Saved: data/fingerprints/95_v33
[Fingerprint v3.3] global=(86, 768)
[Fingerprint v3.3] environment=(86, 640)
[Fingerprint v3.3] color=(86, 48)
[Fingerprint v3.3] spatial=(86, 32)
[Fingerprint v3.3] PATCH STORAGE = DISABLED

{
  "id": "95_v33",
  "version": "3.3",
  "model": "dinov2_vitb14",
  "images": 86,
  "dimension": 768,
  "representatives": 16,
  "patch_tokens": 0,
  "patch_storage": false,
  "environment_descriptor": "compact_v1",
  "environment_dimension": 640,
  "color_descriptor": "hsv_histogram_v1",
  "color_dimension": 48,
  "spatial_descriptor": "gray_grid_v1",
  "spatial_dimension": 32,
  "weights": {
    "global": 0.7,
    "environment": 0.2,
    "color": 0.07,
    "spatial": 0.03
  },
  "image_names": [
    "95_001.JPG",
    "95_002.JPG",
    "95_003.JPG",
    "95_004.JPG",
    "95_005.JPG",
    "95_006.JPG",
    "95_007.JPG",
    "95_008.JPG",
    "95_009.JPG",
    "95_010.JPG",
    "95_011.JPG",
    "95_012.JPG",
    "95_013.JPG",
    "95_014.JPG",
    "95_015.JPG",
    "95_016.JPG",
    "95_017.JPG",
    "95_018.JPG",
    "95_019.JPG",
    "95_020.JPG",
    "95_021.JPG",
    "95_022.JPG",
    "95_023.JPG",
    "95_024.JPG",
    "95_025.JPG",
    "95_026.JPG",
    "95_027.JPG",
    "95_028.JPG",
    "95_029.JPG",
    "95_030.JPG",
    "95_031.JPG",
    "95_032.JPG",
    "95_033.JPG",
    "95_034.JPG",
    "95_035.JPG",
    "95_036.JPG",
    "95_037.JPG",
    "95_038.JPG",
    "95_039.JPG",
    "95_040.JPG",
    "95_041.JPG",
    "95_042.JPG",
    "95_043.JPG",
    "95_044.JPG",
    "95_045.JPG",
    "95_046.JPG",
    "95_047.JPG",
    "95_048.JPG",
    "95_049.JPG",
    "95_050.JPG",
    "95_051.JPG",
    "95_052.JPG",
    "95_053.JPG",
    "95_054.JPG",
    "95_055.JPG",
    "95_056.JPG",
    "95_057.JPG",
    "95_058.JPG",
    "95_059.JPG",
    "95_060.JPG",
    "95_061.JPG",
    "95_062.JPG",
    "95_063.JPG",
    "95_064.JPG",
    "95_065.JPG",
    "95_066.JPG",
    "95_067.JPG",
    "95_068.JPG",
    "95_069.JPG",
    "95_070.JPG",
    "95_071.JPG",
    "95_072.JPG",
    "95_073.JPG",
    "95_074.JPG",
    "95_075.JPG",
    "95_076.JPG",
    "95_077.JPG",
    "95_078.JPG",
    "95_079.JPG",
    "95_080.JPG",
    "95_081.JPG",
    "95_082.JPG",
    "95_083.JPG",
    "95_084.JPG",
    "95_085.JPG",
    "95_086.JPG"
  ]
}
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "============================================================"
echo "=== FINGERPRINT CHECK ==="
echo "============================================================"

for n in $(seq 78 95); do
    p="data/fingerprints/${n}_v33"

    if [ -f "$p/metadata.json" ]; then
        printf "%-12s OK\n" "${n}_v33"
    else
        printf "%-12s ERROR\n" "${n}_v33"
    fi
done

============================================================
=== FINGERPRINT CHECK ===
============================================================
78_v33       OK
79_v33       OK
80_v33       OK
81_v33       OK
82_v33       OK
83_v33       OK
84_v33       OK
85_v33       OK
86_v33       OK
87_v33       OK
88_v33       OK
89_v33       OK
90_v33       OK
91_v33       OK
92_v33       OK
93_v33       OK
94_v33       OK
95_v33       OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
from pathlib import Path
import json

print("=" * 70)
print("FINGERPRINTS")
print("=" * 70)

for n in range(78, 96):
    p = Path(f"data/fingerprints/{n}_v33/metadata.json")

    if not p.exists():
        print(f"{n}_v33 ERROR: metadata missing")
        continue

    d = json.loads(p.read_text(encoding="utf-8"))

    print(
        f"{n}_v33: "
        f"images={len(d.get('image_names', []))} "
        f"version={d.get('version')}"
    )
PY
======================================================================
FINGERPRINTS
======================================================================
78_v33: images=81 version=3.3
79_v33: images=65 version=3.3
80_v33: images=37 version=3.3
81_v33: images=65 version=3.3
82_v33: images=67 version=3.3
83_v33: images=68 version=3.3
84_v33: images=54 version=3.3
85_v33: images=58 version=3.3
86_v33: images=58 version=3.3
87_v33: images=50 version=3.3
88_v33: images=54 version=3.3
89_v33: images=64 version=3.3
90_v33: images=19 version=3.3
91_v33: images=41 version=3.3
92_v33: images=57 version=3.3
93_v33: images=51 version=3.3
94_v33: images=67 version=3.3
95_v33: images=86 version=3.3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 👤 **User** — 2026-08-15 03:45:35

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ echo
echo "============================================================"
echo "=== FINGERPRINT CHECK ==="
echo "============================================================"

for n in $(seq 78 95); do
    p="data/fingerprints/${n}_v33"

    if [ -f "$p/metadata.json" ]; then
        printf "%-12s OK\n" "${n}_v33"
    else
        printf "%-12s ERROR\n" "${n}_v33"
    fi
done

============================================================
=== FINGERPRINT CHECK ===
============================================================
78_v33       OK
79_v33       OK
80_v33       OK
81_v33       OK
82_v33       OK
83_v33       OK
84_v33       OK
85_v33       OK
86_v33       OK
87_v33       OK
88_v33       OK
89_v33       OK
90_v33       OK
91_v33       OK
92_v33       OK
93_v33       OK
94_v33       OK
95_v33       OK
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ python3 - <<'PY'
from pathlib import Path
import json

print("=" * 70)
print("FINGERPRINTS")
print("=" * 70)

for n in range(78, 96):
    p = Path(f"data/fingerprints/{n}_v33/metadata.json")

    if not p.exists():
        print(f"{n}_v33 ERROR: metadata missing")
        continue

    d = json.loads(p.read_text(encoding="utf-8"))

    print(
        f"{n}_v33: "
        f"images={len(d.get('image_names', []))} "
        f"version={d.get('version')}"
    )
PY
======================================================================
FINGERPRINTS
======================================================================
78_v33: images=81 version=3.3
79_v33: images=65 version=3.3
80_v33: images=37 version=3.3
81_v33: images=65 version=3.3
82_v33: images=67 version=3.3
83_v33: images=68 version=3.3
84_v33: images=54 version=3.3
85_v33: images=58 version=3.3
86_v33: images=58 version=3.3
87_v33: images=50 version=3.3
88_v33: images=54 version=3.3
89_v33: images=64 version=3.3
90_v33: images=19 version=3.3
91_v33: images=41 version=3.3
92_v33: images=57 version=3.3
93_v33: images=51 version=3.3
94_v33: images=67 version=3.3
95_v33: images=86 version=3.3
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:45:37

Да, **все 18 слепков `78_v33`–`95_v33` корректно созданы**.

Проверка показывает:

- все каталоги существуют;
- `metadata.json` присутствует;
- у всех `version=3.3`;
- количество изображений записано в metadata;
- ошибок/пропусков нет.

### Следующий шаг

Теперь логично **не трогать сами слепки**, а проверить главное — работает ли старый алгоритм распознавания на этих `v33`.

То есть:

**фото из `test` → распознавание → первый кандидат → присвоение номера → раскладка по папкам `78`, `79`, ... `95`.**

Я бы сейчас сначала сделал **контрольный прогон без копирования файлов**, чтобы увидеть распределение кандидатов и не испортить `test`.

Дай команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

echo "============================================================"
echo "=== TEST RECOGNITION: v33 ==="
echo "============================================================"

uv run scene-fingerprint recognize data/input/test \
  --fingerprints data/fingerprints \
  --top-k 5 \
  --threshold 0.50
```

Но есть важный момент: **если текущая версия `recognize` сама выбирает все доступные fingerprints, нужно проверить, что она действительно берет именно `*_v33`, а не одновременно старые `78`, `78_v31`, `78_v32`, `78_patch` и т.д.**

Поэтому перед запуском я бы сделал ещё одну проверку:

```bash
grep -RniE "fingerprint|v33|_v3|_v32|_v33" app/ | head -100
```

**Пришли вывод этой команды.** Тогда я скажу точную команду для запуска старого алгоритма распознавания именно на `78_v33–95_v33`, не меняя оптимизацию.

---

### 👤 **User** — 2026-08-15 03:46:24

app/core/recognizer.py:17:    Scene Fingerprint v3.3 compact recognizer.
app/core/recognizer.py:103:        fingerprints=None,
app/core/recognizer.py:119:        loaded_fingerprints = []
app/core/recognizer.py:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py:123:        if fingerprints is not None:
app/core/recognizer.py:124:            allowed_fingerprints = {
app/core/recognizer.py:126:                for item in fingerprints
app/core/recognizer.py:130:            allowed_fingerprints = None
app/core/recognizer.py:133:            self.manager.list_fingerprints()
app/core/recognizer.py:135:            fingerprint_id = (
app/core/recognizer.py:139:            if not fingerprint_id:
app/core/recognizer.py:143:                allowed_fingerprints is not None
app/core/recognizer.py:144:                and str(fingerprint_id)
app/core/recognizer.py:145:                not in allowed_fingerprints
app/core/recognizer.py:151:                    fingerprint_id
app/core/recognizer.py:162:                    f"{fingerprint_id}: "
app/core/recognizer.py:177:                    f"fingerprint "
app/core/recognizer.py:178:                    f"{fingerprint_id}"
app/core/recognizer.py:183:            loaded_fingerprints.append(
app/core/recognizer.py:185:                    fingerprint_id,
app/core/recognizer.py:190:        if not loaded_fingerprints:
app/core/recognizer.py:193:                "fingerprints found."
app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py:223:        # They do not depend on the fingerprint.
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:46:27

Отлично. Здесь уже видно главное: **в `recognizer.py` есть whitelist fingerprints**. Значит, мы можем принудительно дать ему только `78_v33`–`95_v33`, и старые версии не будут участвовать.

Но сначала нужно посмотреть точный синтаксис CLI — как `recognize` передаёт параметр `fingerprints`.

Дай одну команду:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
  "add_argument|fingerprints|--fingerprint|--fingerprints" \
  app/cli.py app/ 2>/dev/null | head -150
```

И отдельно очень полезно посмотреть участок самого recognizer:

```bash
sed -n '90,215p' app/core/recognizer.py
```

Пришли оба вывода.

После этого дам **одну готовую команду**, которая:

1. берет `data/input/test`;
2. использует **только `78_v33` ... `95_v33`**;
3. использует текущую оптимизированную обработку;
4. использует именно алгоритм распознавания v3.3;
5. пока **ничего не копирует и не перемещает**;
6. покажет для каждой фотографии **первого кандидата и confidence**.

Это будет безопасный контрольный прогон перед автоматической раскладкой.

---

### 👤 **User** — 2026-08-15 03:47:05

alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ cd ~/projects/scene_fingerprint_mvp_v02

grep -RniE \
  "add_argument|fingerprints|--fingerprint|--fingerprints" \
  app/cli.py app/ 2>/dev/null | head -150
app/cli.py:39:    create_parser.add_argument(
app/cli.py:44:    create_parser.add_argument(
app/cli.py:58:    queue_add_parser.add_argument(
app/cli.py:63:    queue_add_parser.add_argument(
app/cli.py:68:    queue_add_parser.add_argument(
app/cli.py:84:    queue_batch_parser.add_argument(
app/cli.py:90:    queue_batch_parser.add_argument(
app/cli.py:96:    queue_batch_parser.add_argument(
app/cli.py:112:    analyze_parser.add_argument(
app/cli.py:117:    analyze_parser.add_argument(
app/cli.py:118:        "--fingerprint",
app/cli.py:132:    recognize_parser.add_argument(
app/cli.py:137:    recognize_parser.add_argument(
app/cli.py:144:    recognize_parser.add_argument(
app/cli.py:151:    recognize_parser.add_argument(
app/cli.py:158:    recognize_parser.add_argument(
app/cli.py:159:        "--fingerprints",
app/cli.py:165:    recognize_parser.add_argument(
app/cli.py:485:                settings.fingerprints_dir
app/cli.py:619:        selected_fingerprints = None
app/cli.py:621:        if args.fingerprints:
app/cli.py:622:            selected_fingerprints = [
app/cli.py:624:                for item in args.fingerprints.split(",")
app/cli.py:634:                fingerprints=selected_fingerprints,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:103:        fingerprints=None,
app/core/recognizer.py.before_restore_old_matching_20260815_025751:119:        loaded_fingerprints = []
app/core/recognizer.py.before_restore_old_matching_20260815_025751:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.before_restore_old_matching_20260815_025751:123:        if fingerprints is not None:
app/core/recognizer.py.before_restore_old_matching_20260815_025751:124:            allowed_fingerprints = {
app/core/recognizer.py.before_restore_old_matching_20260815_025751:126:                for item in fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:130:            allowed_fingerprints = None
app/core/recognizer.py.before_restore_old_matching_20260815_025751:133:            self.manager.list_fingerprints()
app/core/recognizer.py.before_restore_old_matching_20260815_025751:143:                allowed_fingerprints is not None
app/core/recognizer.py.before_restore_old_matching_20260815_025751:145:                not in allowed_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:183:            loaded_fingerprints.append(
app/core/recognizer.py.before_restore_old_matching_20260815_025751:190:        if not loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025751:193:                "fingerprints found."
app/core/recognizer.py.before_restore_old_matching_20260815_025751:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.before_restore_old_matching_20260815_025751:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025751:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:103:        fingerprints=None,
app/core/recognizer.py.before_restore_old_matching_20260815_025724:119:        loaded_fingerprints = []
app/core/recognizer.py.before_restore_old_matching_20260815_025724:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.before_restore_old_matching_20260815_025724:123:        if fingerprints is not None:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:124:            allowed_fingerprints = {
app/core/recognizer.py.before_restore_old_matching_20260815_025724:126:                for item in fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025724:130:            allowed_fingerprints = None
app/core/recognizer.py.before_restore_old_matching_20260815_025724:133:            self.manager.list_fingerprints()
app/core/recognizer.py.before_restore_old_matching_20260815_025724:143:                allowed_fingerprints is not None
app/core/recognizer.py.before_restore_old_matching_20260815_025724:145:                not in allowed_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025724:183:            loaded_fingerprints.append(
app/core/recognizer.py.before_restore_old_matching_20260815_025724:190:        if not loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025724:193:                "fingerprints found."
app/core/recognizer.py.before_restore_old_matching_20260815_025724:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.before_restore_old_matching_20260815_025724:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025724:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py:103:        fingerprints=None,
app/core/recognizer.py:119:        loaded_fingerprints = []
app/core/recognizer.py:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py:123:        if fingerprints is not None:
app/core/recognizer.py:124:            allowed_fingerprints = {
app/core/recognizer.py:126:                for item in fingerprints
app/core/recognizer.py:130:            allowed_fingerprints = None
app/core/recognizer.py:133:            self.manager.list_fingerprints()
app/core/recognizer.py:143:                allowed_fingerprints is not None
app/core/recognizer.py:145:                not in allowed_fingerprints
app/core/recognizer.py:183:            loaded_fingerprints.append(
app/core/recognizer.py:190:        if not loaded_fingerprints:
app/core/recognizer.py:193:                "fingerprints found."
app/core/recognizer.py:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/config.py:16:    def fingerprints_dir(self):
app/core/config.py:17:        return self.data_dir / "fingerprints"
app/core/fingerprint.py.before_patchfix:17:        self.root = Path(settings.fingerprints_dir)
app/core/fingerprint.py.before_patchfix:23:    def list_fingerprints(self):
app/core/recognizer.py.backup_before_optimization:113:        fingerprints = []
app/core/recognizer.py.backup_before_optimization:116:            self.manager.list_fingerprints()
app/core/recognizer.py.backup_before_optimization:159:            fingerprints.append(
app/core/recognizer.py.backup_before_optimization:166:        if not fingerprints:
app/core/recognizer.py.backup_before_optimization:169:                "fingerprints found."
app/core/recognizer.py.backup_before_optimization:173:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.backup_before_optimization:176:                for fp_id, _ in fingerprints
app/core/recognizer.py.backup_before_optimization:204:            for fingerprint_id, data in fingerprints:
app/core/recognizer.py.before_patchfix:176:        fingerprints = self.manager.list_fingerprints()
app/core/recognizer.py.before_patchfix:180:        for fp in fingerprints:
app/core/fingerprint.py:46:        self.settings.fingerprints_dir.mkdir(
app/core/fingerprint.py:56:            self.settings.fingerprints_dir
app/core/fingerprint.py:60:    def list_fingerprints(self):
app/core/fingerprint.py:64:            self.settings.fingerprints_dir
app/core/recognizer.py.backup_before_force_match:113:        fingerprints = []
app/core/recognizer.py.backup_before_force_match:116:            self.manager.list_fingerprints()
app/core/recognizer.py.backup_before_force_match:159:            fingerprints.append(
app/core/recognizer.py.backup_before_force_match:166:        if not fingerprints:
app/core/recognizer.py.backup_before_force_match:169:                "fingerprints found."
app/core/recognizer.py.backup_before_force_match:173:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.backup_before_force_match:176:                for fp_id, _ in fingerprints
app/core/recognizer.py.backup_before_force_match:204:            for fingerprint_id, data in fingerprints:
app/core/fingerprint.py.bak_before_create_opt:45:        self.settings.fingerprints_dir.mkdir(
app/core/fingerprint.py.bak_before_create_opt:55:            self.settings.fingerprints_dir
app/core/fingerprint.py.bak_before_create_opt:59:    def list_fingerprints(self):
app/core/fingerprint.py.bak_before_create_opt:63:            self.settings.fingerprints_dir
app/core/recognizer.py.v33_working:103:        fingerprints=None,
app/core/recognizer.py.v33_working:119:        loaded_fingerprints = []
app/core/recognizer.py.v33_working:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.v33_working:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.v33_working:123:        if fingerprints is not None:
app/core/recognizer.py.v33_working:124:            allowed_fingerprints = {
app/core/recognizer.py.v33_working:126:                for item in fingerprints
app/core/recognizer.py.v33_working:130:            allowed_fingerprints = None
app/core/recognizer.py.v33_working:133:            self.manager.list_fingerprints()
app/core/recognizer.py.v33_working:143:                allowed_fingerprints is not None
app/core/recognizer.py.v33_working:145:                not in allowed_fingerprints
app/core/recognizer.py.v33_working:183:            loaded_fingerprints.append(
app/core/recognizer.py.v33_working:190:        if not loaded_fingerprints:
app/core/recognizer.py.v33_working:193:                "fingerprints found."
app/core/recognizer.py.v33_working:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.v33_working:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py.v33_working:283:            for fingerprint_id, data in loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025737:103:        fingerprints=None,
app/core/recognizer.py.before_restore_old_matching_20260815_025737:119:        loaded_fingerprints = []
app/core/recognizer.py.before_restore_old_matching_20260815_025737:121:        # Optional whitelist of fingerprints.
app/core/recognizer.py.before_restore_old_matching_20260815_025737:122:        # If provided, ONLY these fingerprints are used.
app/core/recognizer.py.before_restore_old_matching_20260815_025737:123:        if fingerprints is not None:
app/core/recognizer.py.before_restore_old_matching_20260815_025737:124:            allowed_fingerprints = {
app/core/recognizer.py.before_restore_old_matching_20260815_025737:126:                for item in fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025737:130:            allowed_fingerprints = None
app/core/recognizer.py.before_restore_old_matching_20260815_025737:133:            self.manager.list_fingerprints()
app/core/recognizer.py.before_restore_old_matching_20260815_025737:143:                allowed_fingerprints is not None
app/core/recognizer.py.before_restore_old_matching_20260815_025737:145:                not in allowed_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025737:183:            loaded_fingerprints.append(
app/core/recognizer.py.before_restore_old_matching_20260815_025737:190:        if not loaded_fingerprints:
app/core/recognizer.py.before_restore_old_matching_20260815_025737:193:                "fingerprints found."
app/core/recognizer.py.before_restore_old_matching_20260815_025737:197:            "[Recognizer] Fingerprints: "
app/core/recognizer.py.before_restore_old_matching_20260815_025737:200:                for fp_id, _ in loaded_fingerprints
app/core/recognizer.py.before_restore_old_matching_20260815_025737:283:            for fingerprint_id, data in loaded_fingerprints:
app/main.py:73:                    data = manager.list_fingerprints()
app/cli.py:39:    create_parser.add_argument(
app/cli.py:44:    create_parser.add_argument(
app/cli.py:58:    queue_add_parser.add_argument(
app/cli.py:63:    queue_add_parser.add_argument(
app/cli.py:68:    queue_add_parser.add_argument(
app/cli.py:84:    queue_batch_parser.add_argument(
app/cli.py:90:    queue_batch_parser.add_argument(
app/cli.py:96:    queue_batch_parser.add_argument(
app/cli.py:112:    analyze_parser.add_argument(
app/cli.py:117:    analyze_parser.add_argument(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$ sed -n '90,215p' app/core/recognizer.py
            return "PROBABLE_MATCH"

        if confidence == "AMBIGUOUS":
            return "AMBIGUOUS"

        return "NO_MATCH"

    def recognize_folder(
        self,
        folder,
        top_k=5,
        threshold=0.65,
        workers=6,
        fingerprints=None,
    ):
        folder = Path(folder)

        paths = image_files(
            folder
        )

        if not paths:
            return []

        print(
            f"[Recognizer] "
            f"Query images: {len(paths)}"
        )

        loaded_fingerprints = []

        # Optional whitelist of fingerprints.
        # If provided, ONLY these fingerprints are used.
        if fingerprints is not None:
            allowed_fingerprints = {
                str(item).strip()
                for item in fingerprints
                if str(item).strip()
            }
        else:
            allowed_fingerprints = None

        for metadata in (
            self.manager.list_fingerprints()
        ):
            fingerprint_id = (
                metadata.get("id")
            )

            if not fingerprint_id:
                continue

            if (
                allowed_fingerprints is not None
                and str(fingerprint_id)
                not in allowed_fingerprints
            ):
                continue

            try:
                data = self.manager.load(
                    fingerprint_id
                )

            except (
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:

                print(
                    f"[Recognizer] SKIP "
                    f"{fingerprint_id}: "
                    f"{exc}"
                )

                continue

            if str(
                data["metadata"].get(
                    "version",
                    "",
                )
            ) != self.VERSION:

                print(
                    f"[Recognizer] SKIP old "
                    f"fingerprint "
                    f"{fingerprint_id}"
                )

                continue

            loaded_fingerprints.append(
                (
                    fingerprint_id,
                    data,
                )
            )

        if not loaded_fingerprints:
            raise ValueError(
                "No compatible v3.3 compact "
                "fingerprints found."
            )

        print(
            "[Recognizer] Fingerprints: "
            + ", ".join(
                fp_id
                for fp_id, _ in loaded_fingerprints
            )
        )

        # One DINO pass for all query images.
        queries = self.embedder.embed_paths(
            paths
        )

        queries = np.asarray(
            queries,
            dtype=np.float32,
        )

        if queries.ndim == 1:
            queries = queries.reshape(
alexice@NEURO:~/projects/scene_fingerprint_mvp_v02$

---

### 🤖 **Assistant** — 2026-08-15 03:47:06

Да. Теперь всё однозначно.

В текущем `recognizer.py` whitelist работает правильно: если передать `--fingerprints`, будут загружены **только указанные ID**. При этом текущая оптимизация сохраняется — `embed_paths()` делает **один DINO-pass для всех тестовых фотографий**.

И CLI действительно поддерживает:

```text
--fingerprints
```

Причём список передаётся через запятую.

### Делаем контрольный прогон

Сначала **только распознавание**, без сортировки и копирования:

```bash
cd ~/projects/scene_fingerprint_mvp_v02

uv run scene-fingerprint recognize data/input/test \
  --fingerprints 78_v33,79_v33,80_v33,81_v33,82_v33,83_v33,84_v33,85_v33,86_v33,87_v33,88_v33,89_v33,90_v33,91_v33,92_v33,93_v33,94_v33,95_v33 \
  --top-k 5 \
  --threshold 0.50
```

### Что должно быть в начале вывода

Обязательно должно появиться примерно:

```text
[Recognizer] Fingerprints: 78_v33, 79_v33, ..., 95_v33
```

То есть **никаких**:

```text
78
78_patch
78_v31
78_v32
```

и т.д.

После этого пойдут результаты для фотографий.

---

### Важный момент

Мы сейчас проверяем именно ту схему, к которой ты хотел вернуться:

**DINOv2 → v3.3 fingerprint → старый matching → первый кандидат**

При этом новая оптимизация остаётся:

- один проход DINO для всей папки;
- GPU;
- текущая обработка embeddings;
- текущая компактная структура v3.3;
- whitelist `78_v33–95_v33`.

То есть **мы не откатываем весь проект**, а проверяем старый алгоритм сопоставления на новых `v33` слепках.

Запусти эту команду и пришли вывод. Особенно интересует блок:

```text
[Recognizer] Fingerprints: ...
```

и первые ~30–50 результатов распознавания.

---

### 👤 **User** — 2026-08-15 03:49:19

Recognizer] CPU workers: 6

## 00 (1).JPG

MATCH        78_v33
SCORE        0.9468
SECOND       0.8923
MARGIN       0.0545
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_039.JPG

TOP CANDIDATES
1. 78_v33         0.9468
2. 92_v33         0.8923
3. 91_v33         0.8882
4. 95_v33         0.8842
5. 83_v33         0.8808

## 00 (10).JPG

MATCH        78_v33
SCORE        0.9374
SECOND       0.8793
MARGIN       0.0582
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_041.JPG

TOP CANDIDATES
1. 78_v33         0.9374
2. 91_v33         0.8793
3. 93_v33         0.8725
4. 92_v33         0.8708
5. 83_v33         0.8669

## 00 (11).JPG

MATCH        78_v33
SCORE        0.9325
SECOND       0.8903
MARGIN       0.0422
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_041.JPG

TOP CANDIDATES
1. 78_v33         0.9325
2. 95_v33         0.8903
3. 92_v33         0.8824
4. 83_v33         0.8818
5. 91_v33         0.8811

## 00 (12).JPG

MATCH        78_v33
SCORE        0.9294
SECOND       0.8894
MARGIN       0.0400
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_039.JPG

TOP CANDIDATES
1. 78_v33         0.9294
2. 83_v33         0.8894
3. 95_v33         0.8816
4. 91_v33         0.8801
5. 92_v33         0.8770

## 00 (2).JPG

MATCH        78_v33
SCORE        0.9373
SECOND       0.8844
MARGIN       0.0529
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_010.JPG

TOP CANDIDATES
1. 78_v33         0.9373
2. 91_v33         0.8844
3. 95_v33         0.8837
4. 83_v33         0.8818
5. 93_v33         0.8818

## 00 (3).JPG

MATCH        78_v33
SCORE        0.9061
SECOND       0.8515
MARGIN       0.0546
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_012.JPG

TOP CANDIDATES
1. 78_v33         0.9061
2. 93_v33         0.8515
3. 95_v33         0.8499
4. 83_v33         0.8427
5. 92_v33         0.8349

## 00 (4).JPG

MATCH        78_v33
SCORE        0.9510
SECOND       0.8834
MARGIN       0.0676
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_042.JPG

TOP CANDIDATES
1. 78_v33         0.9510
2. 83_v33         0.8834
3. 91_v33         0.8795
4. 92_v33         0.8781
5. 93_v33         0.8762

## 00 (5).JPG

MATCH        78_v33
SCORE        0.9294
SECOND       0.8905
MARGIN       0.0389
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_041.JPG

TOP CANDIDATES
1. 78_v33         0.9294
2. 93_v33         0.8905
3. 92_v33         0.8877
4. 91_v33         0.8798
5. 83_v33         0.8736

## 00 (6).JPG

MATCH        78_v33
SCORE        0.9459
SECOND       0.8897
MARGIN       0.0562
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_039.JPG

TOP CANDIDATES
1. 78_v33         0.9459
2. 92_v33         0.8897
3. 83_v33         0.8847
4. 91_v33         0.8844
5. 85_v33         0.8827

## 00 (7).JPG

MATCH        78_v33
SCORE        0.9333
SECOND       0.9007
MARGIN       0.0326
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_041.JPG

TOP CANDIDATES
1. 78_v33         0.9333
2. 93_v33         0.9007
3. 95_v33         0.8839
4. 92_v33         0.8820
5. 83_v33         0.8733

## 00 (8).JPG

MATCH        79_v33
SCORE        0.9180
SECOND       0.8628
MARGIN       0.0552
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   79_041.JPG

TOP CANDIDATES
1. 79_v33         0.9180
2. 92_v33         0.8628
3. 87_v33         0.8624
4. 83_v33         0.8583
5. 93_v33         0.8371

## 00 (9).JPG

MATCH        78_v33
SCORE        0.9357
SECOND       0.8898
MARGIN       0.0459
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_041.JPG

TOP CANDIDATES
1. 78_v33         0.9357
2. 95_v33         0.8898
3. 91_v33         0.8850
4. 94_v33         0.8761
5. 92_v33         0.8744

## 001.JPG

MATCH        78_v33
SCORE        0.9470
SECOND       0.8886
MARGIN       0.0584
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_075.JPG

TOP CANDIDATES
1. 78_v33         0.9470
2. 91_v33         0.8886
3. 93_v33         0.8870
4. 92_v33         0.8867
5. 83_v33         0.8838

## 002.JPG

MATCH        78_v33
SCORE        0.9469
SECOND       0.8896
MARGIN       0.0573
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_075.JPG

TOP CANDIDATES
1. 78_v33         0.9469
2. 91_v33         0.8896
3. 95_v33         0.8862
4. 92_v33         0.8852
5. 93_v33         0.8815

## 003.JPG

MATCH        78_v33
SCORE        0.9508
SECOND       0.9013
MARGIN       0.0495
CONFIDENCE   HIGH
STATUS       CONFIDENT
BEST IMAGE   78_039.JPG

TOP CANDIDATES
1. 78_v33         0.9508
2. 91_v33         0.9013
3. 83_v33         0.8916
4. 92_v33         0.8915
5. 93_v33         0.8850

---

