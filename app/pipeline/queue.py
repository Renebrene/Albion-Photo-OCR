from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class JobQueue:
    """
    Persistent SQLite job queue.

    States:
        PENDING
        PROCESSING
        DONE
        FAILED
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

        self.db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._init_db()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=30,
        )

        connection.row_factory = sqlite3.Row

        return connection

    @staticmethod
    def _now():
        return datetime.now(
            timezone.utc
        ).isoformat()

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,

                    source_folder TEXT NOT NULL,
                    fingerprint_id TEXT NOT NULL,

                    status TEXT NOT NULL
                        DEFAULT 'PENDING',

                    priority INTEGER NOT NULL
                        DEFAULT 0,

                    attempts INTEGER NOT NULL
                        DEFAULT 0,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,

                    error TEXT
                )
                """
            )

            db.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_jobs_status_priority
                ON jobs(status, priority DESC, id)
                """
            )

    def add(
        self,
        source_folder: str | Path,
        fingerprint_id: str,
        priority: int = 0,
    ):
        created_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                INSERT INTO jobs (
                    source_folder,
                    fingerprint_id,
                    status,
                    priority,
                    attempts,
                    created_at
                )
                VALUES (?, ?, 'PENDING', ?, 0, ?)
                """,
                (
                    str(source_folder),
                    str(fingerprint_id),
                    int(priority),
                    created_at,
                ),
            )

            return int(cursor.lastrowid)

    def list(
        self,
        status: str | None = None,
    ):
        with self._connect() as db:

            if status is None:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    ORDER BY
                        priority DESC,
                        id ASC
                    """
                )
            else:
                cursor = db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE status = ?
                    ORDER BY
                        priority DESC,
                        id ASC
                    """,
                    (status,),
                )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]

    def claim(self):
        """
        Atomically take the next PENDING job.

        Returns:
            dict with job data, or None if queue is empty.
        """

        with self._connect() as db:

            db.execute("BEGIN IMMEDIATE")

            cursor = db.execute(
                """
                SELECT *
                FROM jobs
                WHERE status = 'PENDING'
                ORDER BY
                    priority DESC,
                    id ASC
                LIMIT 1
                """
            )

            row = cursor.fetchone()

            if row is None:
                db.commit()
                return None

            job_id = row["id"]
            started_at = self._now()

            db.execute(
                """
                UPDATE jobs
                SET
                    status = 'PROCESSING',
                    attempts = attempts + 1,
                    started_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PENDING'
                """,
                (
                    started_at,
                    job_id,
                ),
            )

            db.commit()

            return dict(
                db.execute(
                    """
                    SELECT *
                    FROM jobs
                    WHERE id = ?
                    """,
                    (job_id,),
                ).fetchone()
            )

    def complete(self, job_id):
        """
        Mark a processing job as DONE.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'DONE',
                    finished_at = ?,
                    error = NULL
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot complete job {job_id}"
                )

    def fail(self, job_id, error):
        """
        Mark a processing job as FAILED.
        """

        finished_at = self._now()

        with self._connect() as db:
            cursor = db.execute(
                """
                UPDATE jobs
                SET
                    status = 'FAILED',
                    finished_at = ?,
                    error = ?
                WHERE
                    id = ?
                    AND status = 'PROCESSING'
                """,
                (
                    finished_at,
                    str(error),
                    int(job_id),
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError(
                    f"Cannot fail job {job_id}"
                )

    def counts(self):
        with self._connect() as db:
            cursor = db.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM jobs
                GROUP BY status
                """
            )

            return {
                row["status"]: row["count"]
                for row in cursor.fetchall()
            }


if __name__ == "__main__":
    queue = JobQueue(
        "data/jobs.db"
    )

    print("Queue:", queue.db_path)
    print("Counts:", queue.counts())
