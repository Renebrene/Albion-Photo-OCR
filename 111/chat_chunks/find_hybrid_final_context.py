from pathlib import Path
import re

ROOT = Path(".")

TARGETS = [
    r"run_hybrid_v12\.py",
    r"Hybrid v12",
    r"DINO v33.*Hybrid v12",
    r"Hybrid v12.*DINO v33",
    r"frozen Hybrid",
    r"финальн.*DINO",
    r"финальн.*Hybrid",
    r"рабоч.*DINO",
    r"рабоч.*Hybrid",
    r"STABLE.*DINO",
    r"STABLE.*Hybrid",
]

patterns = [re.compile(x, re.IGNORECASE) for x in TARGETS]

files = sorted(
    p for p in ROOT.glob("chunk_*.md")
    if p.is_file()
)

matches = []

for path in files:
    try:
        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except Exception:
        continue

    for i, line in enumerate(lines):
        if any(p.search(line) for p in patterns):
            matches.append((path, i))

# Убираем слишком близкие совпадения из одного места
selected = []
last_by_file = {}

for path, i in matches:
    prev = last_by_file.get(path)
    if prev is not None and i - prev < 15:
        continue

    selected.append((path, i))
    last_by_file[path] = i

print("=" * 110)
print("DINO / HYBRID FINAL CONTEXT SEARCH")
print("=" * 110)
print(f"FILES: {len(files)}")
print(f"RAW MATCHES: {len(matches)}")
print(f"CONTEXT BLOCKS: {len(selected)}")
print()

for n, (path, i) in enumerate(selected, 1):
    start = max(0, i - 25)
    end = min(len(path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()), i + 26)

    lines = path.read_text(
        encoding="utf-8",
        errors="replace"
    ).splitlines()

    print()
    print("#" * 110)
    print(f"BLOCK {n}")
    print(f"FILE: {path}")
    print(f"MATCH LINE: {i + 1}")
    print("#" * 110)

    for j in range(start, end):
        marker = " >>> " if j == i else "     "
        print(f"{marker}{j + 1:5}: {lines[j]}")

