#!/usr/bin/env python3

import json
import shutil
from pathlib import Path

import numpy as np
from sklearn.cluster import AgglomerativeClustering


PROJECT = Path(__file__).resolve().parent.parent

FINGERPRINT_DIR = PROJECT / "data/fingerprints"
INPUT_DIR = PROJECT / "data/input"

OUTPUT_DIR = PROJECT / "output/subclusters"


TARGETS = [
    "84_v33",
    "85_v33",
    "87_v33",
    "89_v33",
    "92_v33",
    "94_v33",
    "95_v33",
]


MAX_CLUSTERS = 3


def find_image(img_name, fp_name):

    # основной вариант:
    # data/input/89/89_01.JPG
    candidates = [
        INPUT_DIR / fp_name.split("_")[0] / img_name,
        INPUT_DIR / fp_name / img_name,
    ]

    for p in candidates:
        if p.exists():
            return p

    return None


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 80)
    print("EXPORT SUBCLUSTERS V33")
    print("=" * 80)


    for fp_name in TARGETS:

        fp_dir = FINGERPRINT_DIR / fp_name

        emb_file = fp_dir / "embeddings.npy"
        meta_file = fp_dir / "metadata.json"


        if not emb_file.exists():
            print("SKIP:", fp_name)
            continue


        with open(
            meta_file,
            encoding="utf-8"
        ) as f:
            meta = json.load(f)


        images = meta.get(
            "image_names",
            []
        )


        if not images:
            print(
                "NO IMAGES:",
                fp_name
            )
            continue


        embeddings = np.load(
            emb_file
        )


        # на случай несовпадения
        n = min(
            len(images),
            len(embeddings)
        )

        images = images[:n]
        embeddings = embeddings[:n]


        clusters = min(
            MAX_CLUSTERS,
            max(2, n // 20)
        )


        model = AgglomerativeClustering(
            n_clusters=clusters
        )


        labels = model.fit_predict(
            embeddings
        )


        out_dir = (
            OUTPUT_DIR /
            fp_name
        )


        if out_dir.exists():
            shutil.rmtree(out_dir)


        out_dir.mkdir(
            parents=True
        )


        print()
        print(fp_name)
        print(
            "images:",
            n,
            "clusters:",
            clusters
        )


        for cid in sorted(set(labels)):

            cluster_dir = (
                out_dir /
                f"cluster_{cid}"
            )

            cluster_dir.mkdir()


            items = [
                img
                for img, label
                in zip(images, labels)
                if label == cid
            ]


            print(
                f"  cluster_{cid}: {len(items)}"
            )


            for img in items:

                src = find_image(
                    img,
                    fp_name
                )

                if src:

                    shutil.copy2(
                        src,
                        cluster_dir / img
                    )


    print()
    print("=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        OUTPUT_DIR
    )


if __name__ == "__main__":
    main()
