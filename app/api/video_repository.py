"""Read/write repository for the isolated durable video-assets domain."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.ingest.database import get_connection

_VIDEO_FIELDS = """
    video_id, filename, display_title, container_format, video_codec,
    width, height, duration_seconds, fps, frame_count, size_bytes,
    taken_at, created_at
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
                "SELECT source_path, filename, size_bytes FROM public.video_assets WHERE video_id = %s",
                (video_id,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return {"source_path": row[0], "filename": row[1], "size_bytes": int(row[2])}


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
                     count(*) FILTER (WHERE kind='video' AND date_trunc('month', created_at)=date_trunc('month', CURRENT_TIMESTAMP))
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
    )
    result = {key: (int(value) if key not in {"period_start", "period_end"} else value) for key, value in zip(names, row)}
    result["months"] = months
    return result


def issue_playback_ticket(video_id: str, action: str, *, ttl_seconds: int = 300) -> tuple[str, datetime]:
    if action not in {"inline", "attachment"}:
        raise ValueError("unsupported ticket action")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.video_playback_tickets WHERE expires_at <= CURRENT_TIMESTAMP")
            cur.execute(
                """INSERT INTO public.video_playback_tickets
                   (ticket_sha256, video_id, action, expires_at)
                   SELECT %s, %s, %s, %s
                   WHERE EXISTS (SELECT 1 FROM public.video_assets WHERE video_id = %s)""",
                (token_hash, video_id, action, expires, video_id),
            )
            if cur.rowcount != 1:
                raise LookupError("video not found")
    return token, expires


def validate_playback_ticket(video_id: str, token: str, action: str) -> bool:
    if action not in {"inline", "attachment"} or not token:
        return False
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT 1 FROM public.video_playback_tickets
                   WHERE ticket_sha256=%s AND video_id=%s AND action=%s
                     AND expires_at > CURRENT_TIMESTAMP""",
                (token_hash, video_id, action),
            )
            return cur.fetchone() is not None
