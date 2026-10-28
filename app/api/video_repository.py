"""Read/write repository for the isolated durable video-assets domain."""

from __future__ import annotations

import hashlib
import math
import os
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from psycopg.types.json import Json

from app.api.config import VIDEO_STORYBOARD_ROOT, display_source_directory
from app.ingest.database import get_connection
from app.video.profiles import PROFILES

STORYBOARD_FRAME_COUNT = 8
MAX_EDIT_VIDEO_BYTES = 1_610_612_736  # 1.5 GiB
MAX_EDIT_VIDEO_DURATION_SECONDS = 10 * 60


def validate_video_edit_limits(size_bytes: int, duration_seconds: float) -> None:
    if int(size_bytes) > MAX_EDIT_VIDEO_BYTES:
        raise ValueError("редактирование доступно для видео размером не более 1,5 ГиБ")
    if float(duration_seconds) > MAX_EDIT_VIDEO_DURATION_SECONDS:
        raise ValueError("редактирование доступно для видео длительностью не более 10 минут")

_VIDEO_FIELDS = """
    video_id, filename, display_title, container_format, video_codec,
    width, height, duration_seconds, fps, frame_count, size_bytes,
    taken_at, created_at, source_path, identity_hash, identity_date, identity_scheme
"""


def _video_row(row) -> dict:
    return {
        "video_id": row[0],
        "filename": row[1],
        "display_title": row[2] or "",
        "container_format": row[3],
        "video_codec": row[4],
        "width": int(row[5]),
        "height": int(row[6]),
        "duration_seconds": float(row[7]),
        "fps": float(row[8]) if row[8] is not None else None,
        "frame_count": int(row[9]) if row[9] is not None else None,
        "size_bytes": int(row[10]),
        "taken_at": row[11],
        "created_at": row[12],
        "source_directory": display_source_directory(str(row[13])) if row[13] else "",
        # Записанный путь нужен, чтобы проверить наличие файла (п. 11); в ответ
        # API он не попадает — VideoSummary объявляет только признак available.
        "source_path": str(row[13]) if row[13] else None,
    }


def list_videos(
    *, limit: int, cursor: str | None = None, query: str | None = None,
    date_from: str | None = None, date_to: str | None = None,
    date_mode: str = "upload",
) -> tuple[list[dict], str | None]:
    if date_mode not in {"upload", "capture"}:
        raise ValueError("date_mode must be upload or capture")
    date_column = "taken_at" if date_mode == "capture" else "created_at"
    clauses = []
    params: list[object] = []
    if cursor:
        clauses.append("video_id > %s")
        params.append(cursor)
    if query:
        clauses.append("(filename ILIKE %s OR display_title ILIKE %s)")
        like = f"%{query}%"
        params.extend((like, like))
    if date_from:
        clauses.append(f"{date_column} >= %s::date")
        params.append(date_from)
    if date_to:
        clauses.append(f"{date_column} < (%s::date + interval '1 day')")
        params.append(date_to)
    sql = f"SELECT {_VIDEO_FIELDS} FROM public.video_assets"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY video_id LIMIT %s"
    params.append(limit + 1)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    has_next = len(rows) > limit
    items = [_video_row(row) for row in rows[:limit]]
    return items, items[-1]["video_id"] if has_next and items else None


def get_video(video_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {_VIDEO_FIELDS} FROM public.video_assets WHERE video_id = %s",
                (video_id,),
            )
            row = cur.fetchone()
    return _video_row(row) if row is not None else None


def video_source(video_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT source_path,filename,size_bytes,COALESCE(identity_hash,sha256),duration_seconds,
                          sha256,identity_hash,identity_date,identity_scheme,taken_at
                   FROM public.video_assets WHERE video_id=%s""",
                (video_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "source_path": row[0], "filename": row[1], "size_bytes": int(row[2]),
        "sha256": str(row[3]) if row[3] is not None else None,
        "duration_seconds": float(row[4]), "content_sha256": row[5],
        "identity_hash": row[6], "identity_date": row[7], "identity_scheme": row[8],
        "taken_at": row[9],
    }


def update_display_title(video_id: str, title: str) -> dict | None:
    title = title.strip()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE public.video_assets SET display_title = %s WHERE video_id = %s RETURNING video_id",
                (title, video_id),
            )
            if cur.fetchone() is None:
                return None
            cur.execute(
                f"SELECT {_VIDEO_FIELDS} FROM public.video_assets WHERE video_id = %s",
                (video_id,),
            )
            row = cur.fetchone()
    return _video_row(row)


def stats() -> dict:
    """Date-series counts use registration/upload time; capture date is separate."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT count(*), min(created_at), max(created_at), max(taken_at)
                   FROM public.video_assets"""
            )
            total, period_start, last_video_at, last_capture_at = cur.fetchone()
            cur.execute(
                """SELECT date_trunc('month', created_at)::date AS month,
                          count(*) AS videos,
                          count(*) FILTER (WHERE taken_at IS NOT NULL) AS with_capture_date
                   FROM public.video_assets
                   GROUP BY date_trunc('month', created_at)
                   ORDER BY month"""
            )
            months = [
                {"month": row[0], "videos": int(row[1]), "with_capture_date": int(row[2])}
                for row in cur.fetchall()
            ]
            cur.execute(
                """SELECT
                     count(*) FILTER (WHERE created_at >= CURRENT_DATE) AS today,
                     count(*) FILTER (WHERE created_at >= CURRENT_DATE - 1
                                      AND created_at < CURRENT_DATE) AS yesterday,
                     count(*) FILTER (WHERE created_at >= CURRENT_DATE - 2
                                      AND created_at < CURRENT_DATE - 1) AS day_before,
                     count(*) FILTER (WHERE created_at >= CURRENT_DATE - 6) AS last_7_days,
                     count(*) FILTER (WHERE date_trunc('month', created_at) = date_trunc('month', CURRENT_DATE)) AS this_month
                   FROM public.video_assets"""
            )
            today, yesterday, day_before, last_7_days, this_month = cur.fetchone()
    return {
        "videos": int(total),
        "period_start": period_start,
        "period_end": last_video_at,
        "last_video_at": last_video_at,
        "last_video_capture_at": last_capture_at,
        "today": int(today),
        "yesterday": int(yesterday),
        "day_before": int(day_before),
        "last_7_days": int(last_7_days),
        "this_month": int(this_month),
        "months": months,
    }


def media_statistics() -> dict:
    """Aggregate upload-time counts for photos and videos together."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.video_assets')")
            has_video_table = cur.fetchone()[0] is not None
            video_rows = (
                "SELECT created_at, 'video'::text AS kind FROM public.video_assets"
                if has_video_table
                else "SELECT NULL::timestamptz AS created_at, 'video'::text AS kind WHERE FALSE"
            )
            video_month_rows = (
                "SELECT date_trunc('month', created_at)::date AS month, 'video'::text AS kind FROM public.video_assets"
                if has_video_table
                else "SELECT NULL::date AS month, 'video'::text AS kind WHERE FALSE"
            )
            cur.execute(
                f"""WITH all_media AS (
                     SELECT created_at, 'photo'::text AS kind FROM public.photos
                     UNION ALL
                     {video_rows}
                   )
                   SELECT
                     count(*) FILTER (WHERE kind='photo'),
                     count(*) FILTER (WHERE kind='video'),
                     min(created_at), max(created_at),
                     count(*) FILTER (WHERE kind='photo' AND created_at >= CURRENT_DATE),
                     count(*) FILTER (WHERE kind='video' AND created_at >= CURRENT_DATE),
                     count(*) FILTER (WHERE kind='photo' AND created_at >= CURRENT_DATE - 1 AND created_at < CURRENT_DATE),
                     count(*) FILTER (WHERE kind='video' AND created_at >= CURRENT_DATE - 1 AND created_at < CURRENT_DATE),
                     count(*) FILTER (WHERE kind='photo' AND created_at >= CURRENT_DATE - 2 AND created_at < CURRENT_DATE - 1),
                     count(*) FILTER (WHERE kind='video' AND created_at >= CURRENT_DATE - 2 AND created_at < CURRENT_DATE - 1),
                     count(*) FILTER (WHERE kind='photo' AND created_at >= CURRENT_DATE - 6),
                     count(*) FILTER (WHERE kind='video' AND created_at >= CURRENT_DATE - 6),
                     count(*) FILTER (WHERE kind='photo' AND date_trunc('month', created_at)=date_trunc('month', CURRENT_TIMESTAMP)),
                     count(*) FILTER (WHERE kind='video' AND date_trunc('month', created_at)=date_trunc('month', CURRENT_TIMESTAMP)),
                     max(created_at) FILTER (WHERE kind='photo'),
                     max(created_at) FILTER (WHERE kind='video')
                   FROM all_media"""
            )
            row = cur.fetchone()
            cur.execute(
                f"""WITH all_media AS (
                     SELECT date_trunc('month', created_at)::date AS month, 'photo'::text AS kind FROM public.photos
                     UNION ALL
                     {video_month_rows}
                   )
                   SELECT month,
                     count(*) FILTER (WHERE kind='photo'),
                     count(*) FILTER (WHERE kind='video')
                   FROM all_media GROUP BY month ORDER BY month"""
            )
            months = [
                {"month": item[0], "photos": int(item[1]), "videos": int(item[2])}
                for item in cur.fetchall()
            ]
    names = (
        "photos", "videos", "period_start", "period_end", "today_photos", "today_videos",
        "yesterday_photos", "yesterday_videos", "day_before_photos", "day_before_videos",
        "last_7_days_photos", "last_7_days_videos", "this_month_photos", "this_month_videos",
        "last_photo_at", "last_video_at",
    )
    result = {
        key: (
            value
            if key in {"period_start", "period_end", "last_photo_at", "last_video_at"}
            else int(value)
        )
        for key, value in zip(names, row)
    }
    result["months"] = months
    return result



def enqueue_transcode(video_id: str, profile: str) -> dict | None:
    """Create or reuse an active/completed derivative and its worker job atomically."""

    if profile not in PROFILES:
        raise ValueError("unsupported transcode profile")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(identity_hash,sha256),size_bytes,duration_seconds,identity_scheme FROM public.video_assets WHERE video_id=%s FOR UPDATE",
                (video_id,),
            )
            asset = cur.fetchone()
            if asset is None:
                return None
            validate_video_edit_limits(asset[1], asset[2])
            source_sha256 = str(asset[0])
            source_identity_scheme = str(asset[3])
            cur.execute(
                """SELECT derivative_id, status, job_id, output_path
                   FROM public.video_derivatives
                   WHERE video_id=%s AND profile=%s AND source_sha256=%s
                   FOR UPDATE""",
                (video_id, profile, source_sha256),
            )
            row = cur.fetchone()
            if row and row[1] in {"PENDING", "RUNNING"}:
                return {"derivative_id": int(row[0]), "job_id": row[2], "status": row[1], "reused": True}
            if row and row[1] == "DONE" and row[3] and Path(row[3]).is_file():
                return {"derivative_id": int(row[0]), "job_id": row[2], "status": "DONE", "reused": True}

            if row:
                derivative_id = int(row[0])
                cur.execute(
                    """UPDATE public.video_derivatives SET status='PENDING', job_id=NULL,
                       output_path=NULL, output_sha256=NULL, output_size_bytes=NULL, output_identity_date=NULL,
                       width=NULL, height=NULL, duration_seconds=NULL, fps=NULL,
                       video_codec=NULL, encoder=NULL, error_message=NULL,
                       source_identity_scheme=%s, started_at=NULL, finished_at=NULL WHERE derivative_id=%s""",
                    (source_identity_scheme, derivative_id),
                )
            else:
                cur.execute(
                    """INSERT INTO public.video_derivatives(
                           video_id,profile,source_sha256,source_identity_scheme,status
                       ) VALUES (%s,%s,%s,%s,'PENDING') RETURNING derivative_id""",
                    (video_id, profile, source_sha256, source_identity_scheme),
                )
                derivative_id = int(cur.fetchone()[0])

            payload = {"video_id": video_id, "profile": profile,
                       "source_sha256": source_sha256, "derivative_id": derivative_id}
            cur.execute(
                """INSERT INTO public.job_queue(job_type, payload, status)
                   VALUES ('VIDEO_TRANSCODE', %s, 'PENDING') RETURNING id""",
                (Json(payload),),
            )
            job_id = int(cur.fetchone()[0])
            cur.execute(
                "UPDATE public.video_derivatives SET job_id=%s WHERE derivative_id=%s",
                (job_id, derivative_id),
            )
            return {"derivative_id": derivative_id, "job_id": job_id, "status": "PENDING", "reused": False}


def normalize_trim_range(start_seconds: float, end_seconds: float) -> tuple[float, float, str]:
    """Millisecond precision keeps request identity and FFmpeg arguments stable."""

    if not math.isfinite(float(start_seconds)) or not math.isfinite(float(end_seconds)):
        raise ValueError("trim times must be finite")
    start = round(float(start_seconds), 3)
    end = round(float(end_seconds), 3)
    if start < 0 or end - start < 0.25:
        raise ValueError("trim range must be at least 0.25 seconds")
    return start, end, f"trim:{start:.3f}:{end:.3f}"


def enqueue_storyboard(video_id: str) -> dict | None:
    """Queue a bounded source-hash-keyed storyboard generation job."""

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COALESCE(identity_hash,sha256) FROM public.video_assets WHERE video_id=%s FOR UPDATE", (video_id,))
            asset = cur.fetchone()
            if asset is None:
                return None
            source_sha256 = str(asset[0])
            cur.execute(
                """SELECT id,status FROM public.job_queue
                   WHERE job_type='VIDEO_STORYBOARD' AND status IN ('PENDING','RUNNING','PAUSED')
                     AND payload ->> 'video_id'=%s AND payload ->> 'source_sha256'=%s
                   ORDER BY id DESC LIMIT 1""",
                (video_id, source_sha256),
            )
            active = cur.fetchone()
            if active:
                return {"job_id": int(active[0]), "status": active[1], "reused": True}
            cur.execute(
                """SELECT id,result FROM public.job_queue
                   WHERE job_type='VIDEO_STORYBOARD' AND status='DONE'
                     AND payload ->> 'video_id'=%s AND payload ->> 'source_sha256'=%s
                   ORDER BY id DESC LIMIT 1""",
                (video_id, source_sha256),
            )
            completed = cur.fetchone()
            if completed and int((completed[1] or {}).get("frames", 0)) == STORYBOARD_FRAME_COUNT:
                from app.video.transcode import _valid_storyboard_frame, storyboard_frame_path

                root = VIDEO_STORYBOARD_ROOT.expanduser().resolve()
                if all(
                    _valid_storyboard_frame(storyboard_frame_path(video_id, source_sha256, index), root)
                    for index in range(STORYBOARD_FRAME_COUNT)
                ):
                    return {"job_id": int(completed[0]), "status": "DONE", "reused": True}
            payload = {"video_id": video_id, "source_sha256": source_sha256}
            cur.execute(
                """INSERT INTO public.job_queue(job_type,payload,status)
                   VALUES ('VIDEO_STORYBOARD',%s,'PENDING')
                   ON CONFLICT ((payload ->> 'video_id'),(payload ->> 'source_sha256'))
                   WHERE job_type='VIDEO_STORYBOARD' AND status IN ('PENDING','RUNNING','PAUSED')
                   DO NOTHING RETURNING id""",
                (Json(payload),),
            )
            row = cur.fetchone()
            if row:
                return {"job_id": int(row[0]), "status": "PENDING", "reused": False}
            cur.execute(
                """SELECT id,status FROM public.job_queue
                   WHERE job_type='VIDEO_STORYBOARD' AND status IN ('PENDING','RUNNING','PAUSED')
                     AND payload ->> 'video_id'=%s AND payload ->> 'source_sha256'=%s
                   ORDER BY id DESC LIMIT 1""",
                (video_id, source_sha256),
            )
            active = cur.fetchone()
            return {"job_id": int(active[0]), "status": active[1], "reused": True} if active else None


def storyboard_ready(video_id: str, source_sha256: str) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT result FROM public.job_queue
                   WHERE job_type='VIDEO_STORYBOARD' AND status='DONE'
                     AND payload ->> 'video_id'=%s AND payload ->> 'source_sha256'=%s
                   ORDER BY id DESC LIMIT 1""",
                (video_id, source_sha256),
            )
            row = cur.fetchone()
    return bool(row and int((row[0] or {}).get("frames", 0)) == STORYBOARD_FRAME_COUNT)


def enqueue_trim(video_id: str, start_seconds: float, end_seconds: float) -> dict | None:
    start, end, operation_key = normalize_trim_range(start_seconds, end_seconds)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(identity_hash,sha256),duration_seconds,size_bytes,identity_scheme FROM public.video_assets WHERE video_id=%s FOR UPDATE",
                (video_id,),
            )
            asset = cur.fetchone()
            if asset is None:
                return None
            validate_video_edit_limits(asset[2], asset[1])
            source_sha256 = str(asset[0])
            source_identity_scheme = str(asset[3])
            if end > float(asset[1]):
                raise ValueError("trim end exceeds source duration")
            cur.execute(
                """SELECT derivative_id,status,job_id,output_path
                   FROM public.video_derivatives
                   WHERE video_id=%s AND source_sha256=%s AND operation_key=%s
                   FOR UPDATE""",
                (video_id, source_sha256, operation_key),
            )
            row = cur.fetchone()
            if row and row[1] in {"PENDING", "RUNNING"}:
                return {"derivative_id": int(row[0]), "job_id": row[2], "status": row[1], "reused": True,
                        "start_seconds": start, "end_seconds": end}
            if row and row[1] == "DONE" and row[3] and Path(row[3]).is_file():
                return {"derivative_id": int(row[0]), "job_id": row[2], "status": "DONE", "reused": True,
                        "start_seconds": start, "end_seconds": end}
            if row:
                derivative_id = int(row[0])
                cur.execute(
                    """UPDATE public.video_derivatives SET status='PENDING',job_id=NULL,
                       output_path=NULL,output_sha256=NULL,output_size_bytes=NULL,
                       width=NULL,height=NULL,duration_seconds=NULL,fps=NULL,
                       video_codec=NULL,encoder=NULL,error_message=NULL,source_identity_scheme=%s,
                       started_at=NULL,finished_at=NULL WHERE derivative_id=%s""",
                    (source_identity_scheme, derivative_id),
                )
            else:
                cur.execute(
                    """INSERT INTO public.video_derivatives(
                           video_id,profile,source_sha256,source_identity_scheme,status,
                           operation_kind,start_seconds,end_seconds,operation_key
                       ) VALUES (%s,'trim',%s,%s,'PENDING','TRIM',%s,%s,%s) RETURNING derivative_id""",
                    (video_id, source_sha256, source_identity_scheme, start, end, operation_key),
                )
                derivative_id = int(cur.fetchone()[0])
            payload = {
                "video_id": video_id,
                "derivative_id": derivative_id,
                "source_sha256": source_sha256,
                "start_seconds": start,
                "end_seconds": end,
                "operation_key": operation_key,
            }
            cur.execute(
                """INSERT INTO public.job_queue(job_type,payload,status)
                   VALUES ('VIDEO_TRIM',%s,'PENDING') RETURNING id""",
                (Json(payload),),
            )
            job_id = int(cur.fetchone()[0])
            cur.execute("UPDATE public.video_derivatives SET job_id=%s WHERE derivative_id=%s", (job_id, derivative_id))
            return {"derivative_id": derivative_id, "job_id": job_id, "status": "PENDING", "reused": False,
                    "start_seconds": start, "end_seconds": end}


def trim_state(video_id: str, start_seconds: float, end_seconds: float) -> dict | None:
    _start, _end, operation_key = normalize_trim_range(start_seconds, end_seconds)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT d.derivative_id,d.status,d.job_id,j.progress,d.start_seconds,d.end_seconds,
                          d.width,d.height,d.duration_seconds,d.fps,d.video_codec,d.encoder,d.error_message,d.finished_at
                   FROM public.video_derivatives d
                   LEFT JOIN public.job_queue j ON j.id=d.job_id
                   WHERE d.video_id=%s AND d.operation_key=%s""",
                (video_id, operation_key),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "derivative_id": int(row[0]), "status": row[1],
        "job_id": int(row[2]) if row[2] is not None else None,
        "progress": row[3], "start_seconds": row[4], "end_seconds": row[5],
        "width": row[6], "height": row[7], "duration_seconds": row[8], "fps": row[9],
        "video_codec": row[10], "encoder": row[11], "error_message": row[12], "finished_at": row[13],
    }


def transcode_state(video_id: str, profile: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT d.derivative_id, d.status, d.job_id, j.progress,
                          d.width, d.height, d.duration_seconds, d.fps,
                          d.video_codec, d.encoder, d.error_message, d.finished_at
                   FROM public.video_derivatives d
                   LEFT JOIN public.job_queue j ON j.id=d.job_id
                   WHERE d.video_id=%s AND d.profile=%s
                   ORDER BY d.created_at DESC LIMIT 1""",
                (video_id, profile),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {
        "derivative_id": int(row[0]), "status": row[1],
        "job_id": int(row[2]) if row[2] is not None else None,
        "progress": row[3], "width": row[4], "height": row[5],
        "duration_seconds": row[6], "fps": row[7], "video_codec": row[8],
        "encoder": row[9], "error_message": row[10], "finished_at": row[11],
    }


def derivative_source(video_id: str, derivative_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT output_path, output_sha256, output_size_bytes
                   FROM public.video_derivatives
                   WHERE video_id=%s AND derivative_id=%s AND status='DONE'""",
                (video_id, derivative_id),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"source_path": row[0], "sha256": row[1], "size_bytes": int(row[2])}


def _register_completed_derivative(cur, derivative_id: int) -> str:
    """Expose one validated managed derivative as a durable video-grid asset."""
    cur.execute(
        """SELECT d.asset_video_id,d.video_id,d.output_path,d.output_sha256,d.output_size_bytes,
                  d.width,d.height,d.duration_seconds,d.fps,d.video_codec,d.derivative_id,
                  a.taken_at,d.output_identity_date,d.source_identity_scheme
           FROM public.video_derivatives d
           JOIN public.video_assets a ON a.video_id=d.video_id
           WHERE d.derivative_id=%s AND d.status='DONE' FOR UPDATE OF d""",
        (derivative_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise LookupError("completed video derivative not found")
    if row[0]:
        return str(row[0])
    path = Path(row[2])
    try:
        root = Path(os.getenv("SCENE_VIDEO_DERIVATIVES_ROOT", str(Path(os.getenv("SCENE_DATA", "data")) / "video_derivatives"))).expanduser().resolve(strict=True)
        path = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("готовая копия видео отсутствует") from exc
    if root not in path.parents or not path.is_file() or not row[4]:
        raise ValueError("готовая копия видео отсутствует")
    stat = path.stat()
    if stat.st_size != int(row[4]):
        raise ValueError("размер готовой копии видео изменился")
    legacy_hash = row[3]
    identity_date = None
    identity_hash = None
    if legacy_hash is not None:
        video_id = f"VI_{str(legacy_hash)[:24]}"
    else:
        from app.ingest.video_register import metadata_identity_hash

        identity_date = row[12] or row[11] or datetime.fromtimestamp(stat.st_mtime, timezone.utc).date()
        if isinstance(identity_date, datetime):
            identity_date = identity_date.astimezone(timezone.utc).date()
        identity_date = identity_date if isinstance(identity_date, date) else date.fromisoformat(str(identity_date))
        identity_hash = metadata_identity_hash(path.name, identity_date, stat.st_size)
        video_id = f"VI_{identity_hash[:24]}"
    cur.execute(
        """INSERT INTO public.video_assets(
               video_id,source_path,filename,sha256,identity_hash,identity_date,identity_scheme,
               container_format,video_codec,width,height,duration_seconds,fps,frame_count,
               size_bytes,taken_at,parent_video_id,source_derivative_id
           ) VALUES (%s,%s,%s,%s,%s,%s,%s,'mp4',%s,%s,%s,%s,%s,NULL,%s,%s,%s,%s)
           ON CONFLICT (video_id) DO NOTHING""",
        (video_id,str(path),path.name,legacy_hash,identity_hash,identity_date,
         "legacy-content-sha256" if legacy_hash is not None else "metadata-v1",
         str(row[9]),int(row[5]),int(row[6]),float(row[7]),row[8],int(row[4]),
         row[11],str(row[1]),int(row[10])),
    )
    lookup_sql = (
        "SELECT video_id FROM public.video_assets WHERE sha256=%s" if legacy_hash is not None
        else "SELECT video_id FROM public.video_assets WHERE identity_hash=%s"
    )
    cur.execute(lookup_sql, (legacy_hash if legacy_hash is not None else identity_hash,))
    identity = cur.fetchone()
    if identity is None:
        raise RuntimeError("не удалось зарегистрировать копию видео")
    video_id = str(identity[0])
    cur.execute(
        "UPDATE public.video_derivatives SET asset_video_id=%s WHERE derivative_id=%s",
        (video_id, derivative_id),
    )
    return video_id


def register_completed_derivative(derivative_id: int) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            return _register_completed_derivative(cur, derivative_id)


def registered_asset_source(video_id: str) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT source_path,duration_seconds FROM public.video_assets WHERE video_id=%s",
                (video_id,),
            )
            row = cur.fetchone()
    return {"source_path": row[0], "duration_seconds": float(row[1])} if row else None


def update_derivative(
    derivative_id: int,
    *,
    status: str,
    job_id: int | None = None,
    error_message: str | None = None,
    result: dict | None = None,
) -> None:
    fields = result or {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE public.video_derivatives SET status=%s,
                     job_id=COALESCE(%s, job_id), error_message=%s,
                     output_path=%s, output_sha256=%s, output_size_bytes=%s,
                     output_identity_date=%s, width=%s, height=%s, duration_seconds=%s, fps=%s,
                     video_codec=%s, encoder=%s,
                     operation_kind=COALESCE(%s, operation_kind),
                     start_seconds=COALESCE(%s, start_seconds),
                     end_seconds=COALESCE(%s, end_seconds),
                     started_at=CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE started_at END,
                     finished_at=CASE WHEN %s THEN CURRENT_TIMESTAMP ELSE finished_at END
                   WHERE derivative_id=%s""",
                (
                    status, job_id, error_message,
                    fields.get("output_path"), fields.get("output_sha256"), fields.get("output_size_bytes"),
                    fields.get("output_identity_date"), fields.get("width"), fields.get("height"), fields.get("duration_seconds"),
                    fields.get("fps"), fields.get("video_codec"), fields.get("encoder"),
                    fields.get("operation_kind"), fields.get("start_seconds"), fields.get("end_seconds"),
                    status == "RUNNING", status in {"DONE", "FAILED", "CANCELLED"}, derivative_id,
                ),
            )
            if cur.rowcount != 1:
                raise LookupError("video derivative not found")
            if status == "DONE":
                _register_completed_derivative(cur, derivative_id)


def issue_playback_ticket(
    video_id: str,
    action: str,
    *,
    derivative_id: int | None = None,
    ttl_seconds: int = 300,
) -> tuple[str, datetime]:
    if action not in {"inline", "attachment", "derivative_attachment"}:
        raise ValueError("unsupported ticket action")
    if (action == "derivative_attachment") != (derivative_id is not None):
        raise ValueError("derivative ticket target is required")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.video_playback_tickets WHERE expires_at <= CURRENT_TIMESTAMP")
            if derivative_id is None:
                cur.execute(
                    """INSERT INTO public.video_playback_tickets
                       (ticket_sha256, video_id, action, expires_at)
                       SELECT %s, %s, %s, %s
                       WHERE EXISTS (SELECT 1 FROM public.video_assets WHERE video_id = %s)""",
                    (token_hash, video_id, action, expires, video_id),
                )
            else:
                cur.execute(
                    """INSERT INTO public.video_playback_tickets
                       (ticket_sha256, video_id, action, derivative_id, expires_at)
                       SELECT %s, %s, %s, derivative_id, %s
                       FROM public.video_derivatives
                       WHERE derivative_id = %s AND video_id = %s AND status = 'DONE'""",
                    (token_hash, video_id, action, expires, derivative_id, video_id),
                )
            if cur.rowcount != 1:
                raise LookupError("video or derivative not found")
    return token, expires


def validate_playback_ticket(
    video_id: str, token: str, action: str, *, derivative_id: int | None = None
) -> bool:
    if action not in {"inline", "attachment", "derivative_attachment"} or not token:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM public.video_playback_tickets
                   WHERE ticket_sha256=%s AND video_id=%s AND action=%s
                     AND derivative_id IS NOT DISTINCT FROM %s
                     AND expires_at > CURRENT_TIMESTAMP""",
                (token_hash, video_id, action, derivative_id),
            )
            return cur.fetchone() is not None
