#!/usr/bin/env python3

from pathlib import Path
import json
import numpy as np

from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score


PROJECT = Path(__file__).resolve().parent.parent

FINGERPRINT_DIR = PROJECT / "data/fingerprints"

MAX_CLUSTERS = 3
MIN_IMAGES_IN_CLUSTER = 3


def analyze_folder(path):

    emb_file = path / "embeddings.npy"
    meta_file = path / "metadata.json"

    if not emb_file.exists():
        return None

    embeddings = np.load(emb_file)

    if len(embeddings) < 6:
        return None

    best = None

    for n in range(2, MAX_CLUSTERS + 1):

        try:
            model = AgglomerativeClustering(
                n_clusters=n
            )

            labels = model.fit_predict(embeddings)

            sizes = [
                np.sum(labels == i)
                for i in range(n)
            ]

            if min(sizes) < MIN_IMAGES_IN_CLUSTER:
                continue

            score = silhouette_score(
                embeddings,
                labels
            )

            if best is None or score > best["score"]:
                best = {
                    "clusters": n,
                    "score": score,
                    "sizes": sizes,
                    "labels": labels
                }

        except Exception:
            pass

    return best


def main():

    print("=" * 80)
    print("SUB-FINGERPRINT ANALYSIS")
    print("=" * 80)
    print()

    for folder in sorted(FINGERPRINT_DIR.iterdir()):

        if not folder.is_dir():
            continue

        result = analyze_folder(folder)

        if result is None:
            continue

        print(folder.name)
        print(
            f" images: {len(np.load(folder/'embeddings.npy'))}"
        )
        print(
            f" clusters: {result['clusters']}"
        )
        print(
            f" silhouette: {result['score']:.3f}"
        )
        print(
            f" sizes: {result['sizes']}"
        )
        print("-" * 80)


if __name__ == "__main__":
    main()
