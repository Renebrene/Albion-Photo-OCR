from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("output/subclusters")
OUT = Path("output/subcluster_contacts")
OUT.mkdir(parents=True, exist_ok=True)

targets = [
    "87_v33/cluster_1",
    "89_v33/cluster_0",
    "92_v33/cluster_0",
    "94_v33/cluster_2",
    "95_v33/cluster_2",
]

THUMB = (250,180)
COLS = 4

for t in targets:
    folder = ROOT / t
    imgs = sorted(folder.glob("*.JPG"))

    if not imgs:
        continue

    rows = (len(imgs)+COLS-1)//COLS

    canvas = Image.new(
        "RGB",
        (COLS*THUMB[0], rows*(THUMB[1]+30)),
        "white"
    )

    draw = ImageDraw.Draw(canvas)

    for i,p in enumerate(imgs):
        im = Image.open(p).convert("RGB")
        im.thumbnail(THUMB)

        x=(i%COLS)*THUMB[0]
        y=(i//COLS)*(THUMB[1]+30)

        canvas.paste(
            im,
            (
                x+(THUMB[0]-im.width)//2,
                y
            )
        )

        draw.text(
            (x+5,y+THUMB[1]+5),
            p.name,
            fill=(0,0,0)
        )

    name=t.replace("/","_")+".jpg"
    canvas.save(OUT/name)

    print(OUT/name)
