from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

# DINO uses the same PostgreSQL database and credentials as INGEST; the shared
# accessor also provides the bounded connection pool.
from app.ingest.database import get_connection  # noqa: F401


@dataclass(frozen=True)
class DinoWorkItem:
    run_id: int
    photo_id: str
    source_path: str
    run_type: str


@dataclass(frozen=True)
class DinoBatch:
    batch_id: int
    run_type: str
    status: str
    total_count: int
    completed_count: int
    failed_count: int


def _validate_run_type(run_type: str) -> None:
    if run_type not in {"NORMAL", "FORCE_RERUN"}:
        raise ValueError(
            f"Unsupported DINO run type: {run_type}"
        )


def create_batch(
    run_type: str = "NORMAL",
    photo_ids: Iterable[str] | None = None,
) -> DinoBatch:
    """
    Create a fixed DINO batch snapshot.

    NORMAL:
        Select all photos which do not yet have a successful DINO run.

    FORCE_RERUN:
        Select only the explicitly supplied photo_ids.

    The selected set is fixed by creating one PENDING dino_runs
    row for every selected photo.
    """
    _validate_run_type(run_type)

    requested_ids = (
        [str(photo_id) for photo_id in photo_ids]
        if photo_ids is not None
        else None
    )

    if run_type == "FORCE_RERUN":
        if not requested_ids:
            raise ValueError(
                "FORCE_RERUN requires at least one photo_id."
            )

        requested_ids = list(dict.fromkeys(requested_ids))

    with get_connection() as conn:
        with conn.cursor() as cur:
            if run_type == "NORMAL":
                cur.execute(
                    """
                    SELECT
                        p.photo_id,
                        p.source_path
                    FROM public.photos AS p
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM public.dino_runs AS r
                        WHERE r.photo_id = p.photo_id
                          AND r.status = 'DONE'
                    )
                    ORDER BY p.photo_id
                    """
                )
            else:
                cur.execute(
                    """
                    SELECT
                        p.photo_id,
                        p.source_path
                    FROM public.photos AS p
                    WHERE p.photo_id = ANY(%s)
                    ORDER BY p.photo_id
                    """,
                    (requested_ids,),
                )

            photos = cur.fetchall()

            if run_type == "FORCE_RERUN":
                found_ids = {str(row[0]) for row in photos}
                missing_ids = [
                    photo_id
                    for photo_id in requested_ids
                    if photo_id not in found_ids
                ]

                if missing_ids:
                    raise ValueError(
                        "FORCE_RERUN photo_id not found: "
                        + ", ".join(missing_ids)
                    )

            cur.execute(
                """
                INSERT INTO public.dino_batches (
                    run_type,
                    status,
                    total_count,
                    completed_count,
                    failed_count
                )
                VALUES (
                    %s,
                    'PENDING',
                    %s,
                    0,
                    0
                )
                RETURNING batch_id
                """,
                (run_type, len(photos)),
            )

            batch_id = int(cur.fetchone()[0])

            if photos:
                cur.executemany(
                    """
                    INSERT INTO public.dino_runs (
                        batch_id,
                        photo_id,
                        run_type,
                        status
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        'PENDING'
                    )
                    """,
                    [
                        (
                            batch_id,
                            photo_id,
                            run_type,
                        )
                        for photo_id, _source_path in photos
                    ],
                )

            cur.execute(
                """
                UPDATE public.dino_batches
                SET
                    status = CASE
                        WHEN total_count = 0 THEN 'DONE'
                        ELSE 'PENDING'
                    END,
                    finished_at = CASE
                        WHEN total_count = 0
                        THEN CURRENT_TIMESTAMP
                        ELSE NULL
                    END
                WHERE batch_id = %s
                """,
                (batch_id,),
            )

            return DinoBatch(
                batch_id=batch_id,
                run_type=run_type,
                status="DONE" if not photos else "PENDING",
                total_count=len(photos),
                completed_count=0,
                failed_count=0,
            )


def get_batch(
    batch_id: int,
) -> DinoBatch | None:
    """
    Return one DINO batch.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    batch_id,
                    run_type,
                    status,
                    total_count,
                    completed_count,
                    failed_count
                FROM public.dino_batches
                WHERE batch_id = %s
                """,
                (batch_id,),
            )

            row = cur.fetchone()

    if row is None:
        return None

    return DinoBatch(
        batch_id=int(row[0]),
        run_type=str(row[1]),
        status=str(row[2]),
        total_count=int(row[3]),
        completed_count=int(row[4]),
        failed_count=int(row[5]),
    )


def get_batch_items(
    batch_id: int,
) -> list[DinoWorkItem]:
    """
    Return the fixed snapshot of one batch.

    Items are returned in photo_id order.
    Their status is preserved so workers can resume PENDING work.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    r.run_id,
                    r.photo_id,
                    p.source_path,
                    r.run_type,
                    r.status
                FROM public.dino_runs AS r
                JOIN public.photos AS p
                  ON p.photo_id = r.photo_id
                WHERE r.batch_id = %s
                ORDER BY r.photo_id
                """,
                (batch_id,),
            )

            rows = cur.fetchall()

    return [
        DinoWorkItem(
            run_id=int(row[0]),
            photo_id=str(row[1]),
            source_path=str(row[2]),
            run_type=str(row[3]),
        )
        for row in rows
        if row[4] == "PENDING"
    ]


def start_batch(
    batch_id: int,
) -> None:
    """
    Move a PENDING batch to RUNNING.

    An already completed or failed batch cannot be started again.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.dino_batches
                SET
                    status = 'RUNNING',
                    started_at = COALESCE(
                        started_at,
                        CURRENT_TIMESTAMP
                    )
                WHERE batch_id = %s
                  AND status = 'PENDING'
                """,
                (batch_id,),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot start DINO batch {batch_id}: "
                    "batch is not PENDING or does not exist."
                )


def start_run(
    run_id: int,
) -> DinoWorkItem:
    """
    Move one batch run from PENDING to RUNNING.

    The source_path is read from PostgreSQL.photos.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    r.run_id,
                    r.photo_id,
                    p.source_path,
                    r.run_type
                FROM public.dino_runs AS r
                JOIN public.photos AS p
                  ON p.photo_id = r.photo_id
                WHERE r.run_id = %s
                  AND r.status = 'PENDING'
                FOR UPDATE OF r
                """,
                (run_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"DINO run {run_id} is not PENDING "
                    "or does not exist."
                )

            cur.execute(
                """
                UPDATE public.dino_runs
                SET
                    status = 'RUNNING',
                    started_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE run_id = %s
                """,
                (run_id,),
            )

            return DinoWorkItem(
                run_id=int(row[0]),
                photo_id=str(row[1]),
                source_path=str(row[2]),
                run_type=str(row[3]),
            )


def save_success(
    run_id: int,
    best_id: str | None,
    score: float,
    second_score: float,
    margin: float,
    confidence: str,
    status: str,
    dino_time_sec: float,
    candidates: list[dict[str, Any]],
) -> None:
    """
    Atomically store one completed DINO run and its TOP candidates.
    """
    if not candidates:
        raise ValueError(
            "DINO success requires at least one candidate."
        )

    candidates = candidates[:5]

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status
                FROM public.dino_runs
                WHERE run_id = %s
                FOR UPDATE
                """,
                (run_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"DINO run not found: {run_id}"
                )

            if row[0] != "RUNNING":
                raise ValueError(
                    f"DINO run {run_id} is not RUNNING: {row[0]}"
                )

            cur.executemany(
                """
                INSERT INTO public.dino_candidates (
                    run_id,
                    rank,
                    fingerprint_id,
                    score,
                    global_score,
                    environment_score,
                    color_score,
                    spatial_score,
                    best_image,
                    best_image_score
                )
                VALUES (
                    %(run_id)s,
                    %(rank)s,
                    %(fingerprint_id)s,
                    %(score)s,
                    %(global_score)s,
                    %(environment_score)s,
                    %(color_score)s,
                    %(spatial_score)s,
                    %(best_image)s,
                    %(best_image_score)s
                )
                ON CONFLICT (run_id, rank) DO UPDATE SET
                    fingerprint_id = EXCLUDED.fingerprint_id,
                    score = EXCLUDED.score,
                    global_score = EXCLUDED.global_score,
                    environment_score = EXCLUDED.environment_score,
                    color_score = EXCLUDED.color_score,
                    spatial_score = EXCLUDED.spatial_score,
                    best_image = EXCLUDED.best_image,
                    best_image_score = EXCLUDED.best_image_score
                """,
                [
                    {
                        "run_id": run_id,
                        "rank": rank,
                        "fingerprint_id": item["id"],
                        "score": float(item["score"]),
                        "global_score": float(item["global"]),
                        "environment_score": float(
                            item["environment"]
                        ),
                        "color_score": float(
                            item["color"]
                        ),
                        "spatial_score": float(
                            item["spatial"]
                        ),
                        "best_image": item.get(
                            "best_image"
                        ),
                        "best_image_score": float(
                            item.get(
                                "best_image_score",
                                0.0,
                            )
                        ),
                    }
                    for rank, item in enumerate(
                        candidates,
                        start=1,
                    )
                ],
            )

            cur.execute(
                """
                UPDATE public.dino_runs
                SET
                    status = 'DONE',
                    dino_best_id = %s,
                    dino_score = %s,
                    dino_second_score = %s,
                    dino_margin = %s,
                    dino_confidence = %s,
                    dino_status = %s,
                    dino_time_sec = %s,
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = NULL
                WHERE run_id = %s
                """,
                (
                    best_id,
                    float(score),
                    float(second_score),
                    float(margin),
                    confidence,
                    status,
                    float(dino_time_sec),
                    run_id,
                ),
            )


def save_failure(
    run_id: int,
    error_message: str,
    dino_time_sec: float,
) -> None:
    """
    Mark a running DINO run as FAILED.

    Previous successful runs remain untouched.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.dino_runs
                SET
                    status = 'FAILED',
                    dino_time_sec = %s,
                    finished_at = CURRENT_TIMESTAMP,
                    error_message = %s
                WHERE run_id = %s
                  AND status = 'RUNNING'
                """,
                (
                    float(dino_time_sec),
                    str(error_message),
                    run_id,
                ),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot fail DINO run {run_id}: "
                    "run is not RUNNING or does not exist."
                )


def finish_batch(
    batch_id: int,
) -> DinoBatch:
    """
    Recalculate batch counters and final state from its runs.

    A batch is DONE only when every run is DONE.
    A batch is FAILED when all runs are finished and at least
    one run is FAILED.
    Otherwise the batch remains RUNNING.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    run_type
                FROM public.dino_batches
                WHERE batch_id = %s
                FOR UPDATE
                """,
                (batch_id,),
            )

            batch_row = cur.fetchone()

            if batch_row is None:
                raise ValueError(
                    f"DINO batch not found: {batch_id}"
                )

            batch_run_type = str(batch_row[0])

            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_count,
                    COUNT(*) FILTER (
                        WHERE status = 'DONE'
                    ) AS completed_count,
                    COUNT(*) FILTER (
                        WHERE status = 'FAILED'
                    ) AS failed_count,
                    COUNT(*) FILTER (
                        WHERE status IN ('PENDING', 'RUNNING')
                    ) AS active_count
                FROM public.dino_runs
                WHERE batch_id = %s
                """,
                (batch_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"DINO batch not found: {batch_id}"
                )

            total_count = int(row[0])
            completed_count = int(row[1])
            failed_count = int(row[2])
            active_count = int(row[3])

            if active_count > 0:
                batch_status = "RUNNING"
                finished = None
            elif failed_count > 0:
                # Any failed run makes the batch terminal and unusable
                # as HYBRID input, even when other runs succeeded.
                batch_status = "FAILED"
                finished = "CURRENT_TIMESTAMP"
            else:
                batch_status = "DONE"
                finished = "CURRENT_TIMESTAMP"

            if finished is None:
                cur.execute(
                    """
                    UPDATE public.dino_batches
                    SET
                        status = %s,
                        completed_count = %s,
                        failed_count = %s
                    WHERE batch_id = %s
                    """,
                    (
                        batch_status,
                        completed_count,
                        failed_count,
                        batch_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE public.dino_batches
                    SET
                        status = %s,
                        completed_count = %s,
                        failed_count = %s,
                        finished_at = CURRENT_TIMESTAMP
                    WHERE batch_id = %s
                    """,
                    (
                        batch_status,
                        completed_count,
                        failed_count,
                        batch_id,
                    ),
                )

            return DinoBatch(
                batch_id=batch_id,
                run_type=batch_run_type,
                status=batch_status,
                total_count=total_count,
                completed_count=completed_count,
                failed_count=failed_count,
            )


def latest_done_run(
    photo_id: str,
) -> dict[str, Any] | None:
    """
    Return the latest successful DINO run for one photo.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    run_id,
                    batch_id,
                    photo_id,
                    run_type,
                    status,
                    dino_best_id,
                    dino_score,
                    dino_second_score,
                    dino_margin,
                    dino_confidence,
                    dino_status,
                    started_at,
                    finished_at,
                    dino_time_sec,
                    error_message,
                    created_at
                FROM public.dino_runs
                WHERE photo_id = %s
                  AND status = 'DONE'
                ORDER BY finished_at DESC, run_id DESC
                LIMIT 1
                """,
                (photo_id,),
            )

            row = cur.fetchone()

            if row is None:
                return None

            columns = [
                "run_id",
                "batch_id",
                "photo_id",
                "run_type",
                "status",
                "dino_best_id",
                "dino_score",
                "dino_second_score",
                "dino_margin",
                "dino_confidence",
                "dino_status",
                "started_at",
                "finished_at",
                "dino_time_sec",
                "error_message",
                "created_at",
            ]

            return dict(zip(columns, row))


def get_candidates(
    run_id: int,
) -> list[dict[str, Any]]:
    """
    Return TOP candidates for one DINO run in rank order.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    rank,
                    fingerprint_id,
                    score,
                    global_score,
                    environment_score,
                    color_score,
                    spatial_score,
                    best_image,
                    best_image_score
                FROM public.dino_candidates
                WHERE run_id = %s
                ORDER BY rank
                """,
                (run_id,),
            )

            rows = cur.fetchall()

    columns = [
        "rank",
        "fingerprint_id",
        "score",
        "global_score",
        "environment_score",
        "color_score",
        "spatial_score",
        "best_image",
        "best_image_score",
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]


def requeue_stale_runs(*, older_than_minutes: int = 30) -> int:
    """
    Return DINO runs stuck in RUNNING (older than the threshold) to PENDING.

    A crashed worker can leave a run RUNNING forever; the job queue recovery
    alone does not fix that, so the batch would never finish. Returns how many
    runs were reset. Candidates already written for such a run are safe to
    rewrite (save_success upserts), but a run is only reset if it is still
    RUNNING (never a completed one).
    """

    if older_than_minutes < 0:
        raise ValueError("older_than_minutes must be >= 0")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.dino_runs
                SET
                    status = 'PENDING',
                    started_at = NULL,
                    error_message = COALESCE(error_message || ' | ', '')
                        || 'requeued (stale RUNNING)'
                WHERE status = 'RUNNING'
                  AND started_at IS NOT NULL
                  AND started_at < CURRENT_TIMESTAMP
                        - (%s || ' minutes')::interval
                """,
                (str(int(older_than_minutes)),),
            )
            return cur.rowcount


def has_active_batch() -> bool:
    """True when a DINO batch is still PENDING or RUNNING."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM public.dino_batches "
                "WHERE status IN ('PENDING', 'RUNNING') LIMIT 1"
            )
            return cur.fetchone() is not None
