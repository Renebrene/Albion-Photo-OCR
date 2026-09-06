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

OUTPUT_DIR = PROJECT / "output/sequence_v38_1"

SORTED_DIR = OUTPUT_DIR / "sorted"


MARGIN_LIMIT = 0.02

WINDOW = 3


DIST_WEIGHT = {
    1: 5,
    2: 3,
    3: 1,
}



def norm_id(x):

    if x is None:
        return None

    s=str(x)

    if "_" in s:
        s=s.split("_")[0]

    try:
        return int(s)

    except:
        return None



def candidate_list(row):

    result=[]

    for k in (
        "top1",
        "top2",
        "top3",
        "top4",
        "top5",
    ):

        x=norm_id(row.get(k))

        if x is not None:
            result.append(x)

    return result



def main():

    with open(
        SOURCE_JSON,
        encoding="utf-8"
    ) as f:

        data=json.load(f)


    rows=data["results"]


    rows=[
        r for r in rows
        if (
            INPUT_DIR /
            Path(r["file"]).name
        ).exists()
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


        margin=(
            float(row["top1_score"])
            -
            float(row["top2_score"])
        )


        final=top1

        reason="KEEP"


        if margin < MARGIN_LIMIT:


            votes=Counter()

            left_support=Counter()
            right_support=Counter()


            for dist in range(1, WINDOW+1):

                weight=DIST_WEIGHT[dist]


                for side in (-1,1):

                    j=i+side*dist


                    if j<0 or j>=len(rows):
                        continue


                    cands=candidate_list(rows[j])


                    if not cands:
                        continue


                    candidate=cands[0]


                    votes[candidate]+=weight


                    if side==-1:
                        left_support[candidate]+=weight
                    else:
                        right_support[candidate]+=weight



            if votes:


                best,count=votes.most_common(1)[0]


                current=votes.get(
                    top1,
                    0
                )


                # проверяем, что кандидат поддерживается
                # с обеих сторон

                both_sides = (
                    left_support.get(best,0)>0
                    and
                    right_support.get(best,0)>0
                )


                if (
                    best != top1
                    and
                    count >= current + 4
                    and
                    both_sides
                ):

                    final=best

                    reason=(
                        f"CHANGE {count}>{current}"
                    )

                    changed.append(
                        {
                            "image":image,
                            "old":top1,
                            "new":final,
                            "margin":margin,
                            "votes":dict(votes),
                            "left":dict(left_support),
                            "right":dict(right_support),
                        }
                    )



        decisions.append(
            {
                "image":image,
                "final":final,
                "top1":top1,
                "top2":top2,
                "margin":margin,
                "reason":reason,
            }
        )



    # копирование


    for d in decisions:

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
            INPUT_DIR/d["image"],
            dst
        )



    print("="*80)
    print("SEQUENCE V38.1 RESULT")
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

    for c in changed:

        print(
            c["image"]
        )

        print(
            f"{c['old']} -> {c['new']}"
        )

        print(
            "votes:",
            c["votes"]
        )

        print(
            "left:",
            c["left"]
        )

        print(
            "right:",
            c["right"]
        )

        print()



    print("OUTPUT:")
    print(SORTED_DIR)



if __name__=="__main__":
    main()

