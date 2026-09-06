#!/usr/bin/env python3

import json
import shutil
from pathlib import Path
from collections import Counter


PROJECT = Path(__file__).resolve().parent.parent

INPUT_DIR = PROJECT / "data/input/test"

SOURCE_JSON = (
    PROJECT /
    "data/output/benchmark_v1/benchmark.json"
)

OUTPUT_DIR = PROJECT / "output/sequence_v38"

SORTED_DIR = OUTPUT_DIR / "sorted"


MARGIN_LIMIT = 0.02

WINDOW = 5


def norm_id(x):

    if x is None:
        return None

    s = str(x)

    if "_" in s:
        s = s.split("_")[0]

    try:
        return int(s)

    except:
        return None



def candidates(row):

    result = []

    for k in (
        "top1",
        "top2",
        "top3",
        "top4",
        "top5"
    ):

        x = norm_id(row.get(k))

        if x is not None:
            result.append(x)

    return result



def main():

    with open(SOURCE_JSON, encoding="utf-8") as f:
        data=json.load(f)


    rows=data["results"]


    rows=[
        r for r in rows
        if (INPUT_DIR / Path(r["file"]).name).exists()
    ]


    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    SORTED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    decisions=[]

    changed=[]


    for i,row in enumerate(rows):

        image=Path(row["file"]).name


        top1=norm_id(row["top1"])
        top2=norm_id(row["top2"])


        s1=float(row["top1_score"])
        s2=float(row["top2_score"])


        margin=s1-s2


        final=top1
        reason="KEEP_TOP1"



        if margin < MARGIN_LIMIT:


            votes=Counter()


            # окно соседей

            start=max(
                0,
                i-WINDOW
            )

            end=min(
                len(rows),
                i+WINDOW+1
            )


            for j in range(start,end):

                if j==i:
                    continue


                nr=rows[j]


                nc=candidates(nr)


                # сильнее голосуем за TOP1

                if nc:

                    votes[nc[0]] += 2


                    for c in nc[1:3]:
                        votes[c] += 1



            if votes:


                best_vote, best_count = votes.most_common(1)[0]


                current_votes=votes.get(
                    top1,
                    0
                )


                if (
                    best_vote != top1
                    and best_count >= current_votes + 2
                ):

                    final=best_vote

                    reason=(
                        "SEQUENCE_OVERRIDE "
                        f"{best_count}>{current_votes}"
                    )

                    changed.append(
                        {
                            "image":image,
                            "old":top1,
                            "new":final,
                            "margin":margin,
                            "votes":dict(votes),
                            "reason":reason
                        }
                    )


        decisions.append(
            {
                "image":image,
                "final":final,
                "top1":top1,
                "top2":top2,
                "margin":margin,
                "reason":reason
            }
        )


    # сортировка


    for d in decisions:

        src=INPUT_DIR/d["image"]

        dst=(
            SORTED_DIR /
            str(d["final"]) /
            d["image"]
        )

        dst.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            src,
            dst
        )


    dist=Counter(
        d["final"]
        for d in decisions
    )


    print("="*80)
    print("SEQUENCE V38 RESULT")
    print("="*80)

    print(
        "Images:",
        len(decisions)
    )

    print(
        "Changed:",
        len(changed)
    )


    print()

    for x in changed:

        print(
            x["image"]
        )

        print(
            f"{x['old']} -> {x['new']}"
        )

        print(
            x["reason"]
        )

        print(
            x["votes"]
        )

        print()



    print("DISTRIBUTION")
    print("-"*80)


    for k in sorted(dist):

        print(
            f"{k:<5} {dist[k]:4d}"
        )


    print()
    print(
        "OUTPUT:",
        SORTED_DIR
    )



if __name__=="__main__":
    main()

