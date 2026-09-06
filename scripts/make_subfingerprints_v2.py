#!/usr/bin/env python3

import json
import shutil
import sys
from pathlib import Path

import numpy as np


# ============================================================
# SETTINGS
# ============================================================

WEIGHTS = {
    "global": 0.70,
    "environment": 0.20,
    "color": 0.07,
    "spatial": 0.03,
}

MIN_CORE = 5
MAX_CORE = 25

# Минимальная близость для попадания в локальную группу.
CORE_THRESHOLD = 0.84

# Если две группы слишком похожи — считаем их дубликатами.
MERGE_JACCARD = 0.50

# Сколько представителей хранить в каждом subfingerprint.
REPRESENTATIVES = 5


# ============================================================
# UTILS
# ============================================================

def normalize_rows(x):
    x = x.astype(np.float32, copy=False)
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / (norms + 1e-12)


def cosine_matrix(x):
    x = normalize_rows(x)
    return x @ x.T


def load_descriptor(path):
    return normalize_rows(np.load(path).astype(np.float32))


def combined_similarity(p, n):
    """
    Комбинированная similarity-матрица.

    Каждый descriptor нормализуется отдельно.
    Затем используется v33 weighting.
    """

    print("Loading descriptors...")

    global_x = load_descriptor(p / "embeddings.npy")
    env_x = load_descriptor(p / "environment_embeddings.npy")
    color_x = load_descriptor(p / "color_embeddings.npy")
    spatial_x = load_descriptor(p / "spatial_embeddings.npy")

    print(f"  global:      {global_x.shape}")
    print(f"  environment: {env_x.shape}")
    print(f"  color:       {color_x.shape}")
    print(f"  spatial:     {spatial_x.shape}")

    print("Building similarity matrices...")

    S = (
        WEIGHTS["global"] * (global_x @ global_x.T)
        + WEIGHTS["environment"] * (env_x @ env_x.T)
        + WEIGHTS["color"] * (color_x @ color_x.T)
        + WEIGHTS["spatial"] * (spatial_x @ spatial_x.T)
    )

    np.fill_diagonal(S, 1.0)

    return S, global_x


def choose_representatives(indices, global_x, count=REPRESENTATIVES):
    """
    Выбираем наиболее центральные изображения внутри группы.
    """

    if len(indices) <= count:
        return list(indices)

    X = global_x[indices]

    center = X.mean(axis=0)
    center /= np.linalg.norm(center) + 1e-12

    scores = X @ center

    order = np.argsort(-scores)

    return [indices[i] for i in order[:count]]


def group_jaccard(a, b):
    a = set(a)
    b = set(b)

    inter = len(a & b)
    union = len(a | b)

    if union == 0:
        return 0.0

    return inter / union


# ============================================================
# BUILD LOCAL GROUPS
# ============================================================

def build_groups(S):
    n = len(S)

    unused = set(range(n))
    groups = []

    # Чем больше средняя similarity кандидата с остальными,
    # тем более устойчивым будет seed.
    mean_sim = S.copy()
    np.fill_diagonal(mean_sim, 0)

    centrality = mean_sim.sum(axis=1) / max(n - 1, 1)

    while unused:

        # Берём наиболее центральную ещё не использованную точку.
        seed = max(
            unused,
            key=lambda i: centrality[i]
        )

        candidates = [
            i for i in unused
            if S[seed, i] >= CORE_THRESHOLD
        ]

        # Если группа слишком большая, оставляем ближайшие к seed.
        if len(candidates) > MAX_CORE:
            candidates = sorted(
                candidates,
                key=lambda i: S[seed, i],
                reverse=True
            )[:MAX_CORE]

        # Слишком маленькая группа — seed пока просто
        # исключаем из рассмотрения.
        if len(candidates) < MIN_CORE:
            unused.remove(seed)
            continue

        groups.append({
            "seed": seed,
            "members": sorted(candidates),
            "seed_score": float(centrality[seed]),
        })

        # ВАЖНО:
        # полностью удаляем участников только если они уже
        # попали в устойчивое ядро. Это допускает overlap.
        for i in candidates:
            unused.discard(i)

    return groups


# ============================================================
# MERGE DUPLICATES
# ============================================================

def merge_groups(groups):
    changed = True

    while changed:
        changed = False

        for i in range(len(groups)):
            if changed:
                break

            for j in range(i + 1, len(groups)):

                a = groups[i]["members"]
                b = groups[j]["members"]

                jac = group_jaccard(a, b)

                if jac >= MERGE_JACCARD:

                    # Оставляем более крупную / более устойчивую группу.
                    if len(a) >= len(b):
                        keep, remove = i, j
                    else:
                        keep, remove = j, i

                    merged = sorted(
                        set(groups[keep]["members"])
                        | set(groups[remove]["members"])
                    )

                    groups[keep]["members"] = merged

                    groups.pop(remove)

                    changed = True
                    break

    return groups


# ============================================================
# SAVE
# ============================================================

def save_groups(
    fingerprint,
    source,
    output_root,
    groups,
    global_x,
    image_names,
    S,
):
    output = output_root / fingerprint

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(parents=True)

    for num, group in enumerate(groups, 1):

        members = group["members"]
        seed = group["seed"]

        sub_name = f"sub_{num:02d}"
        sub_dir = output / sub_name
        sub_dir.mkdir()

        reps = choose_representatives(
            members,
            global_x,
            REPRESENTATIVES,
        )

        # centroid
        centroid = global_x[members].mean(axis=0)
        centroid /= np.linalg.norm(centroid) + 1e-12

        np.save(
            sub_dir / "centroid.npy",
            centroid.astype(np.float32),
        )

        np.save(
            sub_dir / "representatives.npy",
            global_x[reps].astype(np.float32),
        )

        np.save(
            sub_dir / "representative_indices.npy",
            np.asarray(reps, dtype=np.int32),
        )

        np.save(
            sub_dir / "member_indices.npy",
            np.asarray(members, dtype=np.int32),
        )

        # Средняя similarity членов к centroid
        member_scores = global_x[members] @ centroid
        mean_score = float(member_scores.mean())

        metadata = {
            "subfingerprint": sub_name,
            "parent": fingerprint,
            "version": "2.0",

            "members": len(members),

            "seed_index": int(seed),
            "seed_image": image_names[seed],

            "mean_similarity_to_centroid": mean_score,

            "representatives": [
                image_names[i]
                for i in reps
            ],

            "images": [
                image_names[i]
                for i in members
            ],

            "weights": WEIGHTS,

            "threshold": CORE_THRESHOLD,
            "min_core": MIN_CORE,
            "max_core": MAX_CORE,
        }

        with open(
            sub_dir / "metadata.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                metadata,
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(
            f"  {sub_name:<8} "
            f"members={len(members):3d} "
            f"seed={seed:3d} "
            f"seed_image={image_names[seed]} "
            f"mean={mean_score:.4f}"
        )

    return output


# ============================================================
# MAIN
# ============================================================

def main():

    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "  uv run python scripts/make_subfingerprints_v2.py 78_v33"
        )
        sys.exit(1)

    fingerprint = sys.argv[1]

    source = Path("data/fingerprints") / fingerprint

    if not source.exists():
        print(f"ERROR: fingerprint not found: {source}")
        sys.exit(1)

    with open(
        source / "metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    image_names = metadata["image_names"]
    n = len(image_names)

    print()
    print("=" * 70)
    print("SUBFINGERPRINTS V2")
    print("=" * 70)
    print(f"FINGERPRINT: {fingerprint}")
    print(f"IMAGES:      {n}")
    print()
    print("WEIGHTS:")
    for k, v in WEIGHTS.items():
        print(f"  {k:<12} {v}")
    print()
    print(f"CORE_THRESHOLD: {CORE_THRESHOLD}")
    print(f"MIN_CORE:       {MIN_CORE}")
    print(f"MAX_CORE:       {MAX_CORE}")
    print(f"MERGE_JACCARD:  {MERGE_JACCARD}")
    print()

    S, global_x = combined_similarity(
        source,
        n,
    )

    print()
    print("Building local groups...")

    groups = build_groups(S)

    print(
        f"Initial groups: {len(groups)}"
    )

    groups = merge_groups(groups)

    print(
        f"After merge:    {len(groups)}"
    )

    print()
    print("FINAL GROUPS")
    print("-" * 70)

    output = save_groups(
        fingerprint,
        source,
        Path("data/subfingerprints_v2"),
        groups,
        global_x,
        image_names,
        S,
    )

    print()
    print("=" * 70)
    print(f"OUTPUT: {output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
