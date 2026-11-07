#!/usr/bin/env python3
"""Wait for DINO batch 1 to finish, then create and run a HYBRID baseline."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dino.database import get_batch  # noqa: E402
from app.hybrid.database import create_run  # noqa: E402

BATCH_ID = 1
POLL_SECONDS = 60


def main() -> int:
    while True:
        batch = get_batch(BATCH_ID)
        if batch is None:
            print(f"[watcher] batch {BATCH_ID} not found", flush=True)
            return 2
        print(
            f"[watcher] batch {BATCH_ID} status={batch.status} "
            f"done={batch.completed_count} failed={batch.failed_count}",
            flush=True,
        )
        if batch.status == "DONE":
            break
        if batch.status in {"FAILED", "ABORTED", "CANCELLED"}:
            print(f"[watcher] batch ended as {batch.status}", flush=True)
            return 1
        time.sleep(POLL_SECONDS)

    run = create_run(BATCH_ID)
    print(
        f"[watcher] HYBRID run {run.hybrid_run_id} created "
        f"for batch {BATCH_ID}",
        flush=True,
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.hybrid.runner",
            str(run.hybrid_run_id),
        ],
        check=False,
    )
    print(f"[watcher] HYBRID exit={result.returncode}", flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
