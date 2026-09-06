#!/usr/bin/env python3

import argparse
import json
import shutil
from pathlib import Path

import numpy as np


def normalize(x):
    x = x.astype(np.float32, copy=False)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.maximum(n, 1e-12)


def build_similarity(X):
    X = normalize(X)
    return X @ X.T


def make_groups(
    similarity,
    min_similarity=0.84,
    seed_similarity=0.88,
    min_group_size=5,
):
    """
    Строит перекрывающиеся локальные группы.

    seed:
        кадр должен иметь достаточно сильное локальное окружение.

    member:
        кадр попадает в группу, если достаточно похож
        на центральный кадр.

    Группы могут пересекаться.
    """

    n = len(similarity)

    # Среднее сходство каждой фотографии.
    mean_sim = (similarity.sum(axis=1) - 1.0) / max(n - 1, 1)

    # Чем выше среднее сходство, тем более центральный кадр.
    order = np.argsort(mean_sim)[::-1]

    groups = []
    used_as_seed = set()

    for seed in order:
        if seed in used_as_seed:
            continue

        # Кандидаты вокруг seed.
        members = np.where(similarity[seed] >= min_similarity)[0]

        # Сам seed обязательно входит.
        if seed not in members:
            members = np.append(members, seed)

        members = np.unique(members)

        if len(members) < min_group_size:
            continue

        # Для seed нужен достаточно плотный локальный кластер.
        local = members[members != seed]

        if len(local) > 0:
            local_mean = float(similarity[seed, local].mean())
        else:
            local_mean = 1.0

        if local_mean < seed_similarity:
            continue

        # Не создаём практически одинаковые группы.
        duplicate = False

        current = set(int(x) for x in members)

        for g in groups:
            old = set(g["members"])

            intersection = len(current & old)
            union = len(current | old)

            jaccard = intersection / max(union, 1)

            if jaccard >= 0.75:
                duplicate = True
                break

        if duplicate:
            continue

        groups.append(
            {
                "seed": int(seed),
                "members": sorted(int(x) for x in members),
                "mean_similarity": local_mean,
            }
        )

        used_as_seed.add(int(seed))

    return groups, mean_sim


def add_isolated_groups(
    groups,
    mean_sim,
    similarity,
    min_mean_similarity=0.60,
):
    """
    Сохраняет редкие кадры как отдельные subfingerprint.

    Это особенно важно для случаев вроде 81_v33,
    где один кадр сильно отличается от остальных.
    """

    assigned = set()

    for g in groups:
        assigned.update(g["members"])

    n = len(mean_sim)

    for i in range(n):
        if i in assigned:
            continue

        # Если кадр действительно не похож на основную массу,
        # сохраняем его как отдельный subfingerprint.
        if mean_sim[i] < min_mean_similarity:
            groups.append(
                {
                    "seed": int(i),
                    "members": [int(i)],
                    "mean_similarity": float(mean_sim[i]),
                    "isolated": True,
                }
            )

    return groups


def create_subfingerprint(
    source,
    output,
    group_id,
    group,
    embeddings,
    environment,
    color,
    spatial,
    image_names,
    representatives_per_group=5,
):
    members = np.asarray(group["members"], dtype=np.int32)

    # Глобальный centroid.
    global_vectors = embeddings[members]
    centroid = global_vectors.mean(axis=0)
    centroid /= max(np.linalg.norm(centroid), 1e-12)

    # Остальные descriptor'ы тоже усредняем.
    env = environment[members].mean(axis=0)
    col = color[members].mean(axis=0)
    spa = spatial[members].mean(axis=0)

    # Представители — реальные фотографии,
    # наиболее близкие к centroid.
    X = normalize(global_vectors)

    c = centroid.reshape(1, -1)
    scores = (X @ c.T).reshape(-1)

    order = np.argsort(scores)[::-1]

    rep_count = min(
        representatives_per_group,
        len(members),
    )

    rep_local = order[:rep_count]
    rep_indices = members[rep_local]

    out = output / group_id
    out.mkdir(parents=True, exist_ok=True)

    np.save(out / "centroid.npy", centroid.astype(np.float32))
    np.save(out / "environment.npy", env.astype(np.float32))
    np.save(out / "color.npy", col.astype(np.float32))
    np.save(out / "spatial.npy", spa.astype(np.float32))

    np.save(out / "member_indices.npy", members)

    np.save(
        out / "representative_indices.npy",
        rep_indices.astype(np.int32),
    )

    np.save(
        out / "representatives.npy",
        embeddings[rep_indices].astype(np.float32),
    )

    metadata = {
        "source_fingerprint": source.name,
        "subfingerprint": group_id,
        "members": int(len(members)),
        "isolated": bool(group.get("isolated", False)),
        "seed_index": int(group["seed"]),
        "seed_image": image_names[group["seed"]],
        "mean_similarity_to_seed": float(
            group["mean_similarity"]
        ),
        "images": [
            image_names[int(i)]
            for i in members
        ],
        "representatives": [
            image_names[int(i)]
            for i in rep_indices
        ],
    }

    with open(
        out / "metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2,
        )


def process_fingerprint(
    fingerprint,
    fingerprints_root,
    output_root,
    min_similarity,
    seed_similarity,
    min_group_size,
):
    source = fingerprints_root / fingerprint

    if not source.exists():
        raise FileNotFoundError(source)

    required = [
        "embeddings.npy",
        "environment_embeddings.npy",
        "color_embeddings.npy",
        "spatial_embeddings.npy",
        "metadata.json",
    ]

    for name in required:
        if not (source / name).exists():
            raise FileNotFoundError(
                f"{source / name} not found"
            )

    embeddings = np.load(
        source / "embeddings.npy"
    ).astype(np.float32)

    environment = np.load(
        source / "environment_embeddings.npy"
    ).astype(np.float32)

    color = np.load(
        source / "color_embeddings.npy"
    ).astype(np.float32)

    spatial = np.load(
        source / "spatial_embeddings.npy"
    ).astype(np.float32)

    with open(
        source / "metadata.json",
        "r",
        encoding="utf-8",
    ) as f:
        metadata = json.load(f)

    image_names = metadata["image_names"]

    if len(image_names) != len(embeddings):
        raise RuntimeError(
            f"{fingerprint}: image_names={len(image_names)} "
            f"but embeddings={len(embeddings)}"
        )

    print()
    print("=" * 70)
    print(f"FINGERPRINT: {fingerprint}")
    print(f"IMAGES:      {len(embeddings)}")

    similarity = build_similarity(embeddings)

    groups, mean_sim = make_groups(
        similarity,
        min_similarity=min_similarity,
        seed_similarity=seed_similarity,
        min_group_size=min_group_size,
    )

    groups = add_isolated_groups(
        groups,
        mean_sim,
        similarity,
    )

    # Сортировка:
    # сначала большие группы, затем одиночные.
    groups.sort(
        key=lambda g: (
            bool(g.get("isolated", False)),
            -len(g["members"]),
        )
    )

    output = output_root / fingerprint

    if output.exists():
        shutil.rmtree(output)

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    summary = {
        "fingerprint": fingerprint,
        "images": len(embeddings),
        "subfingerprints": len(groups),
        "parameters": {
            "min_similarity": min_similarity,
            "seed_similarity": seed_similarity,
            "min_group_size": min_group_size,
        },
        "groups": [],
    }

    for number, group in enumerate(groups, start=1):
        group_id = f"sub_{number:02d}"

        create_subfingerprint(
            source=source,
            output=output,
            group_id=group_id,
            group=group,
            embeddings=embeddings,
            environment=environment,
            color=color,
            spatial=spatial,
            image_names=image_names,
        )

        summary["groups"].append(
            {
                "id": group_id,
                "members": len(group["members"]),
                "isolated": bool(
                    group.get("isolated", False)
                ),
                "seed_index": group["seed"],
                "seed_image": image_names[group["seed"]],
                "mean_similarity": group["mean_similarity"],
            }
        )

    with open(
        output / "metadata.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"SUBFINGERPRINTS: {len(groups)}")

    for g in summary["groups"]:
        print(
            f"  {g['id']:8s}"
            f" members={g['members']:3d}"
            f" seed={g['seed_index']:3d}"
            f" mean={g['mean_similarity']:.4f}"
            f"{' ISOLATED' if g['isolated'] else ''}"
        )

    print()
    print(f"OUTPUT: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Create subfingerprints from existing v3.3 fingerprints"
    )

    parser.add_argument(
        "fingerprint",
        help="Fingerprint ID, e.g. 78_v33",
    )

    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.84,
    )

    parser.add_argument(
        "--seed-similarity",
        type=float,
        default=0.88,
    )

    parser.add_argument(
        "--min-group-size",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--fingerprints-root",
        default="data/fingerprints",
    )

    parser.add_argument(
        "--output-root",
        default="data/subfingerprints",
    )

    args = parser.parse_args()

    process_fingerprint(
        fingerprint=args.fingerprint,
        fingerprints_root=Path(
            args.fingerprints_root
        ),
        output_root=Path(
            args.output_root
        ),
        min_similarity=args.min_similarity,
        seed_similarity=args.seed_similarity,
        min_group_size=args.min_group_size,
    )


if __name__ == "__main__":
    main()
