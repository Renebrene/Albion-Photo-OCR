from dataclasses import dataclass
from typing import Any

# Same database/credentials as INGEST, including the bounded connection pool.
from app.ingest.database import get_connection  # noqa: F401


@dataclass(frozen=True)
class HybridWorkItem:
    photo_id: str
    dino_run_id: int
    dino_best_id: str | None
    dino_score: float | None
    dino_second_score: float | None
    dino_margin: float | None
    dino_confidence: str | None
    dino_status: str | None
    candidates: list[dict[str, Any]]


def filter_active_candidates(
    candidates: list[dict[str, Any]],
    best_id: str | None,
    active: set[str] | None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Drop candidates of hidden fingerprints from a saved DINO result."""

    if active is None:
        return candidates, best_id

    kept = [
        candidate for candidate in candidates if candidate["id"] in active
    ]

    if best_id is not None and best_id not in active:
        best_id = None

    return kept, best_id


@dataclass(frozen=True)
class HybridRun:
    hybrid_run_id: int
    dino_batch_id: int
    status: str
    total_count: int
    completed_count: int
    failed_count: int


def _create_run_in_transaction(cur, dino_batch_id: int) -> HybridRun:
    """Create a HYBRID row after validating the immutable DINO batch input."""

    cur.execute(
        """
        SELECT status, total_count, failed_count
        FROM public.dino_batches
        WHERE batch_id = %s
        FOR UPDATE
        """,
        (dino_batch_id,),
    )

    batch = cur.fetchone()
    if batch is None:
        raise ValueError(f"DINO batch not found: {dino_batch_id}")

    status = str(batch[0])
    total_count = int(batch[1])
    failed_count = int(batch[2])

    if status != "DONE":
        raise ValueError(f"DINO batch {dino_batch_id} is not DONE: {status}")

    cur.execute(
        """
        SELECT COUNT(*) FILTER (WHERE status = 'DONE'),
               COUNT(*) FILTER (WHERE status = 'FAILED')
        FROM public.dino_runs
        WHERE batch_id = %s
        """,
        (dino_batch_id,),
    )
    done_runs, failed_runs = map(int, cur.fetchone())

    # Every run must be finished. Separate unreadable files may stay FAILED:
    # they simply carry no verdict, and HYBRID sorts the rest of the corpus.
    # A batch with no DONE run at all is not DONE itself (see finish_batch).
    if done_runs + failed_runs != total_count:
        raise ValueError(
            f"DINO batch {dino_batch_id} has unfinished runs: "
            f"DONE={done_runs}, FAILED={failed_runs}, TOTAL={total_count}"
        )
    if done_runs == 0:
        raise ValueError(
            f"DINO batch {dino_batch_id} produced no results: "
            f"FAILED={failed_count}, TOTAL={total_count}"
        )

    cur.execute(
        """
        INSERT INTO public.hybrid_runs (
            dino_batch_id, status, total_count, completed_count, failed_count
        )
        VALUES (%s, %s, %s, 0, 0)
        RETURNING hybrid_run_id
        """,
        (dino_batch_id, "DONE" if not done_runs else "PENDING", done_runs),
    )
    hybrid_run_id = int(cur.fetchone()[0])

    if not done_runs:
        cur.execute(
            "UPDATE public.hybrid_runs SET finished_at=CURRENT_TIMESTAMP "
            "WHERE hybrid_run_id=%s",
            (hybrid_run_id,),
        )

    return HybridRun(
        hybrid_run_id=hybrid_run_id,
        dino_batch_id=dino_batch_id,
        status="DONE" if not done_runs else "PENDING",
        total_count=done_runs,
        completed_count=0,
        failed_count=0,
    )


def create_run(dino_batch_id: int) -> HybridRun:
    """Create a HYBRID RUN for one completed DINO batch."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            return _create_run_in_transaction(cur, int(dino_batch_id))


def create_and_enqueue_run(
    dino_batch_id: int,
    *,
    run_history_id: int | None = None,
    history_spec: dict | None = None,
) -> tuple[HybridRun, int | None, int | None]:
    """
    Atomically create one HYBRID run and its queue job/history link.

    A worker/API failure cannot leave a new PENDING HYBRID row without a
    corresponding queue job. The caller-owned transaction also links the
    follow-on job before run history can be finalized by the DINO job.
    """

    from app.jobs.database import enqueue_in_transaction
    from app.runs import history

    create_history = bool(history_spec and history.available())
    new_history_id = None
    new_history_counts = None
    job_id = None

    with get_connection() as conn:
        with conn.cursor() as cur:
            hybrid = _create_run_in_transaction(cur, int(dino_batch_id))

            active_history_id = run_history_id
            if active_history_id is not None:
                cur.execute(
                    "SELECT 1 FROM public.run_history WHERE run_id=%s",
                    (int(active_history_id),),
                )
                if cur.fetchone() is None:
                    active_history_id = None

            if active_history_id is None and create_history:
                spec = dict(history_spec or {})
                title_prefix = str(spec.pop("title_prefix", "HYBRID run"))
                new_history_id = history.create_run_in_transaction(
                    cur,
                    kind="sort",
                    mode=spec.pop("mode", "manual"),
                    title=f"{title_prefix} #{hybrid.hybrid_run_id}",
                    total=hybrid.total_count,
                    counts=spec.pop(
                        "counts",
                        history.initial_sort_counts(
                            hybrid.total_count, dino=False, hybrid=True
                        ),
                    ),
                    source_id=hybrid.hybrid_run_id,
                    status="RUNNING" if hybrid.total_count else "PENDING",
                    started=True,
                    **spec,
                )
                active_history_id = new_history_id

            if hybrid.total_count:
                job_id = enqueue_in_transaction(
                    cur,
                    "HYBRID_RUN",
                    {"hybrid_run_id": hybrid.hybrid_run_id},
                    run_history_id=active_history_id,
                )
                if active_history_id is not None:
                    history.link_job_in_transaction(
                        cur, int(active_history_id), job_id
                    )
                    history.set_sort_stage_in_transaction(
                        cur,
                        int(active_history_id),
                        "HYBRID",
                        status="RUNNING",
                        total=hybrid.total_count,
                        required=True,
                    )
            elif active_history_id is not None:
                history.set_sort_stage_in_transaction(
                    cur,
                    int(active_history_id),
                    "HYBRID",
                    status="SKIPPED",
                    total=0,
                    required=False,
                )

            if new_history_id is not None:
                new_history_counts = history.finish_enqueue_in_transaction(
                    cur,
                    new_history_id,
                    total=hybrid.total_count,
                    covered=hybrid.total_count,
                )

    if new_history_id is not None:
        log_lines = [
            f"run created: kind=sort mode=manual title=HYBRID run #{hybrid.hybrid_run_id}"
        ]
        if new_history_counts and not new_history_counts.get("jobs_total") and not new_history_counts.get("total"):
            log_lines.append("run finished: no new jobs")
        try:
            history.append_log(new_history_id, log_lines)
        except Exception:
            # Logging must not hide the already committed run and queue job.
            pass

    return hybrid, job_id, new_history_id


def fail_unstarted_run_in_transaction(cur, hybrid_run_id: int) -> bool:
    """Close a queued HYBRID run if its queue job is cancelled before claim."""

    cur.execute(
        """
        UPDATE public.hybrid_runs
        SET status='FAILED',
            failed_count=total_count,
            finished_at=CURRENT_TIMESTAMP
        WHERE hybrid_run_id=%s AND status='PENDING'
        """,
        (int(hybrid_run_id),),
    )
    return cur.rowcount == 1


def get_run(
    hybrid_run_id: int,
) -> HybridRun:
    """Return one HYBRID RUN."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    hybrid_run_id,
                    dino_batch_id,
                    status,
                    total_count,
                    completed_count,
                    failed_count
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"HYBRID run not found: {hybrid_run_id}"
                )

            return HybridRun(
                hybrid_run_id=int(row[0]),
                dino_batch_id=int(row[1]),
                status=str(row[2]),
                total_count=int(row[3]),
                completed_count=int(row[4]),
                failed_count=int(row[5]),
            )


def get_run_items(
    hybrid_run_id: int,
) -> list[HybridWorkItem]:
    """
    Return the complete fixed input of one HYBRID RUN.

    Input is resolved strictly through:
        hybrid_run -> dino_batch -> dino_runs -> dino_candidates

    No photo files are read.
    """

    # Hidden fingerprints must not take part in HYBRID either. The candidates
    # of an older DINO batch can still contain them, so filter here too (and
    # clear a saved DINO best that now points at a hidden fingerprint).
    from app.api.fingerprints import active_fingerprint_ids

    active = active_fingerprint_ids()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dino_batch_id
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"HYBRID run not found: {hybrid_run_id}"
                )

            dino_batch_id = int(row[0])

            cur.execute(
                """
                SELECT
                    r.run_id,
                    r.photo_id,
                    r.dino_best_id,
                    r.dino_score,
                    r.dino_second_score,
                    r.dino_margin,
                    r.dino_confidence,
                    r.dino_status
                FROM public.dino_runs AS r
                JOIN public.photos AS p
                  ON p.photo_id = r.photo_id
                WHERE r.batch_id = %s
                  AND r.status = 'DONE'
                ORDER BY p.filename
                """,
                (dino_batch_id,),
            )

            runs = cur.fetchall()

            items: list[HybridWorkItem] = []

            for run in runs:
                run_id = int(run[0])

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

                candidate_rows = cur.fetchall()

                if not candidate_rows:
                    raise ValueError(
                        f"HYBRID input is incomplete: "
                        f"DINO run {run_id} has no candidates"
                    )

                candidates = [
                    {
                        "rank": int(candidate[0]),
                        "id": str(candidate[1]),
                        "score": float(candidate[2]),
                        "global_score": float(candidate[3]),
                        "environment_score": float(candidate[4]),
                        "color_score": float(candidate[5]),
                        "spatial_score": float(candidate[6]),
                        "best_image": candidate[7],
                        "best_image_score": float(candidate[8]),
                    }
                    for candidate in candidate_rows
                ]

                best_id = str(run[2]) if run[2] is not None else None
                candidates, best_id = filter_active_candidates(
                    candidates, best_id, active
                )

                items.append(
                    HybridWorkItem(
                        photo_id=str(run[1]),
                        dino_run_id=run_id,
                        dino_best_id=best_id,
                        dino_score=(
                            float(run[3]) if run[3] is not None else None
                        ),
                        dino_second_score=(
                            float(run[4]) if run[4] is not None else None
                        ),
                        dino_margin=(
                            float(run[5]) if run[5] is not None else None
                        ),
                        dino_confidence=(
                            str(run[6]) if run[6] is not None else None
                        ),
                        dino_status=(
                            str(run[7]) if run[7] is not None else None
                        ),
                        candidates=candidates,
                    )
                )

            if len(items) != get_run(hybrid_run_id).total_count:
                raise ValueError(
                    f"HYBRID input is incomplete for run {hybrid_run_id}: "
                    f"{len(items)}/{get_run(hybrid_run_id).total_count}"
                )

            return items


def start_run(
    hybrid_run_id: int,
) -> HybridRun:
    """Move a HYBRID RUN from PENDING to RUNNING."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.hybrid_runs
                SET
                    status = 'RUNNING',
                    started_at = CURRENT_TIMESTAMP
                WHERE hybrid_run_id = %s
                  AND status = 'PENDING'
                """,
                (hybrid_run_id,),
            )

            if cur.rowcount != 1:
                raise ValueError(
                    f"Cannot start HYBRID run {hybrid_run_id}: "
                    "run is not PENDING or does not exist."
                )

    return get_run(hybrid_run_id)


def save_success(
    hybrid_run_id: int,
    photo_id: str,
    dino_run_id: int,
    hybrid_original_id: str | None,
    hybrid_final_id: str | None,
    hybrid_changed: bool,
    hybrid_old_score: float | None,
    hybrid_score: float | None,
    hybrid_margin: float | None,
    hybrid_neighbors: str | None,
    hybrid_time_sec: float,
) -> None:
    """
    Save one successful HYBRID result.

    Idempotent for a (hybrid_run_id, photo_id) pair: a retried or recovered
    run overwrites its previous row instead of failing on the primary key.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dino_batch_id,
                    status
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            run = cur.fetchone()

            if run is None:
                raise ValueError(
                    f"HYBRID run not found: {hybrid_run_id}"
                )

            if str(run[1]) != "RUNNING":
                raise ValueError(
                    f"Cannot save HYBRID result for run {hybrid_run_id}: "
                    f"status is {run[1]}"
                )

            dino_batch_id = int(run[0])

            cur.execute(
                """
                SELECT 1
                FROM public.dino_runs
                WHERE run_id = %s
                  AND batch_id = %s
                  AND photo_id = %s
                  AND status = 'DONE'
                """,
                (
                    dino_run_id,
                    dino_batch_id,
                    photo_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "DINO run does not belong to the HYBRID input batch "
                    "or is not DONE."
                )

            cur.execute(
                """
                INSERT INTO public.hybrid_results (
                    hybrid_run_id,
                    photo_id,
                    dino_run_id,
                    hybrid_original_id,
                    hybrid_final_id,
                    hybrid_changed,
                    hybrid_old_score,
                    hybrid_score,
                    hybrid_margin,
                    hybrid_neighbors,
                    status,
                    error_message,
                    hybrid_time_sec,
                    finished_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    'DONE', NULL, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (hybrid_run_id, photo_id) DO UPDATE SET
                    dino_run_id = EXCLUDED.dino_run_id,
                    hybrid_original_id = EXCLUDED.hybrid_original_id,
                    hybrid_final_id = EXCLUDED.hybrid_final_id,
                    hybrid_changed = EXCLUDED.hybrid_changed,
                    hybrid_old_score = EXCLUDED.hybrid_old_score,
                    hybrid_score = EXCLUDED.hybrid_score,
                    hybrid_margin = EXCLUDED.hybrid_margin,
                    hybrid_neighbors = EXCLUDED.hybrid_neighbors,
                    status = 'DONE',
                    error_message = NULL,
                    hybrid_time_sec = EXCLUDED.hybrid_time_sec,
                    finished_at = CURRENT_TIMESTAMP
                """,
                (
                    hybrid_run_id,
                    photo_id,
                    dino_run_id,
                    hybrid_original_id,
                    hybrid_final_id,
                    bool(hybrid_changed),
                    hybrid_old_score,
                    hybrid_score,
                    hybrid_margin,
                    (
                        str(hybrid_neighbors)
                        if hybrid_neighbors is not None
                        else None
                    ),
                    float(hybrid_time_sec),
                ),
            )


def save_failure(
    hybrid_run_id: int,
    photo_id: str,
    dino_run_id: int,
    error_message: str,
    hybrid_time_sec: float,
) -> None:
    """Save one failed HYBRID result."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    dino_batch_id,
                    status
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            run = cur.fetchone()

            if run is None:
                raise ValueError(
                    f"HYBRID run not found: {hybrid_run_id}"
                )

            if str(run[1]) != "RUNNING":
                raise ValueError(
                    f"Cannot save HYBRID failure for run {hybrid_run_id}: "
                    f"status is {run[1]}"
                )

            dino_batch_id = int(run[0])

            cur.execute(
                """
                SELECT 1
                FROM public.dino_runs
                WHERE run_id = %s
                  AND batch_id = %s
                  AND photo_id = %s
                  AND status = 'DONE'
                """,
                (
                    dino_run_id,
                    dino_batch_id,
                    photo_id,
                ),
            )

            if cur.fetchone() is None:
                raise ValueError(
                    "DINO run does not belong to the HYBRID input batch "
                    "or is not DONE."
                )

            cur.execute(
                """
                INSERT INTO public.hybrid_results (
                    hybrid_run_id,
                    photo_id,
                    dino_run_id,
                    hybrid_original_id,
                    hybrid_final_id,
                    hybrid_changed,
                    hybrid_old_score,
                    hybrid_score,
                    hybrid_margin,
                    hybrid_neighbors,
                    status,
                    error_message,
                    hybrid_time_sec,
                    finished_at
                )
                VALUES (
                    %s, %s, %s, NULL, NULL, FALSE, NULL, NULL, NULL, NULL,
                    'FAILED', %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (hybrid_run_id, photo_id) DO UPDATE SET
                    dino_run_id = EXCLUDED.dino_run_id,
                    status = 'FAILED',
                    error_message = EXCLUDED.error_message,
                    hybrid_time_sec = EXCLUDED.hybrid_time_sec,
                    finished_at = CURRENT_TIMESTAMP
                """,
                (
                    hybrid_run_id,
                    photo_id,
                    dino_run_id,
                    str(error_message),
                    float(hybrid_time_sec),
                ),
            )


def finish_run(
    hybrid_run_id: int,
) -> HybridRun:
    """
    Recalculate HYBRID RUN counters and final state.

    DONE only when every result is DONE.
    FAILED when every result is finished and at least one is FAILED.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    total_count
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                FOR UPDATE
                """,
                (hybrid_run_id,),
            )

            row = cur.fetchone()

            if row is None:
                raise ValueError(
                    f"HYBRID run not found: {hybrid_run_id}"
                )

            total_count = int(row[0])

            cur.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE status = 'DONE'
                    ) AS completed_count,
                    COUNT(*) FILTER (
                        WHERE status = 'FAILED'
                    ) AS failed_count,
                    COUNT(*) FILTER (
                        WHERE status IN ('PENDING', 'RUNNING')
                    ) AS active_count
                FROM public.hybrid_results
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            result = cur.fetchone()

            completed_count = int(result[0])
            failed_count = int(result[1])
            active_count = int(result[2])

            if active_count > 0 or (
                completed_count + failed_count < total_count
            ):
                status = "RUNNING"
                finished = False
            elif failed_count > 0:
                status = "FAILED"
                finished = True
            else:
                status = "DONE"
                finished = True

            if finished:
                cur.execute(
                    """
                    UPDATE public.hybrid_runs
                    SET
                        status = %s,
                        completed_count = %s,
                        failed_count = %s,
                        finished_at = CURRENT_TIMESTAMP
                    WHERE hybrid_run_id = %s
                    """,
                    (
                        status,
                        completed_count,
                        failed_count,
                        hybrid_run_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE public.hybrid_runs
                    SET
                        status = %s,
                        completed_count = %s,
                        failed_count = %s
                    WHERE hybrid_run_id = %s
                    """,
                    (
                        status,
                        completed_count,
                        failed_count,
                        hybrid_run_id,
                    ),
                )

            cur.execute(
                """
                SELECT
                    dino_batch_id
                FROM public.hybrid_runs
                WHERE hybrid_run_id = %s
                """,
                (hybrid_run_id,),
            )

            dino_batch_id = int(cur.fetchone()[0])

            return HybridRun(
                hybrid_run_id=hybrid_run_id,
                dino_batch_id=dino_batch_id,
                status=status,
                total_count=total_count,
                completed_count=completed_count,
                failed_count=failed_count,
            )


def completed_photo_ids(hybrid_run_id: int) -> set[str]:
    """photo_ids that already have a DONE result in this HYBRID run."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT photo_id
                FROM public.hybrid_results
                WHERE hybrid_run_id = %s
                  AND status = 'DONE'
                """,
                (hybrid_run_id,),
            )
            return {str(row[0]) for row in cur.fetchall()}


def requeue_stale_runs(*, older_than_minutes: int = 30) -> int:
    """
    Return HYBRID runs stuck in RUNNING (older than the threshold) to PENDING.

    Only the run status is reset; any results already written are kept and the
    rerun is idempotent (save_success upserts), so recovery does not lose
    completed work.
    """

    if older_than_minutes < 0:
        raise ValueError("older_than_minutes must be >= 0")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE public.hybrid_runs
                SET
                    status = 'PENDING',
                    started_at = NULL
                WHERE status = 'RUNNING'
                  AND started_at IS NOT NULL
                  AND started_at < CURRENT_TIMESTAMP
                        - (%s || ' minutes')::interval
                """,
                (str(int(older_than_minutes)),),
            )
            return cur.rowcount
