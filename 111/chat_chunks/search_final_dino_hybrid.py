from pathlib import Path
import re

ROOT = Path(".")

PATTERNS = {
    "DINO": [
        r"\bdino\b",
        r"dinov2",
        r"dino_worker",
        r"embedder",
    ],
    "HYBRID": [
        r"\bhybrid\b",
        r"hybrid[_ -]?v?\d+",
        r"run_hybrid",
    ],
    "VERSION": [
        r"\bv12\b",
        r"\bv33\b",
        r"\bv3\.3\b",
        r"v\d+[_-]?working",
        r"final",
        r"финаль",
        r"финал",
        r"рабоч",
        r"working",
        r"restore",
        r"восстанов",
    ],
    "RECOGNITION": [
        r"recognizer",
        r"recognition",
        r"распозна",
        r"match",
        r"top[-_ ]?5",
        r"top[-_ ]?k",
        r"candidate",
        r"кандидат",
    ],
    "SEQUENCE": [
        r"neighbor",
        r"sequence",
        r"consensus",
        r"сосед",
        r"последоват",
        r"subfingerprint",
        r"subfinger",
    ],
    "FILES": [
        r"\.py\b",
        r"fingerprint\.py",
        r"recognizer\.py",
        r"hybrid",
        r"dino",
    ],
}

compiled = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in PATTERNS.items()
}

def categories_for(line):
    result = []
    for category, patterns in compiled.items():
        if any(p.search(line) for p in patterns):
            result.append(category)
    return result

files = sorted(
    p for p in ROOT.rglob("*")
    if p.is_file()
    and p.name != Path(__file__).name
)

hits = []

for path in files:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        continue

    for lineno, line in enumerate(text.splitlines(), 1):
        categories = categories_for(line)
        if categories:
            hits.append(
                (
                    len(categories),
                    path,
                    lineno,
                    categories,
                    line.strip(),
                )
            )

# Most informative lines first, then file/line.
hits.sort(
    key=lambda x: (-x[0], str(x[1]), x[2])
)

print("=" * 100)
print("FINAL DINO / HYBRID SEARCH")
print("=" * 100)
print(f"ROOT: {ROOT.resolve()}")
print(f"FILES SCANNED: {len(files)}")
print(f"HITS: {len(hits)}")
print()

for score, path, lineno, categories, line in hits:
    print(
        f"[{score}] "
        f"{','.join(categories):<32} "
        f"{path}:{lineno}"
    )
    print(f"    {line[:500]}")
