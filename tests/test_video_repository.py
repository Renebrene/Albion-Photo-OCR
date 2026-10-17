from __future__ import annotations

from contextlib import contextmanager

from app.api import video_repository


class _Cursor:
    def __init__(self, has_video_table):
        self.has_video_table = has_video_table
        self.current = None
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(sql)
        if "to_regclass" in sql:
            self.current = ("video_assets" if self.has_video_table else None,)
        elif "WITH all_media" in sql and "GROUP BY month" not in sql:
            self.current = (
                2, 0, "2024-01-01", "2026-10-15", 0, 0, 1, 0, 0, 0,
                1, 0, 1, 0, "2026-10-15T10:00:00", None,
            )
        elif "GROUP BY month" in sql:
            self.rows = [("2024-01-01", 1, 0), ("2026-10-01", 1, 0)]
        else:
            raise AssertionError(f"unexpected SQL: {sql}")

    def fetchone(self):
        return self.current

    def fetchall(self):
        return getattr(self, "rows", [])

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _Connection:
    def __init__(self, has_video_table):
        self.cursor_value = _Cursor(has_video_table)

    def cursor(self):
        return self.cursor_value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_media_stats_is_backward_compatible_before_video_migration(monkeypatch):
    connection = _Connection(has_video_table=False)

    @contextmanager
    def fake_connection():
        yield connection

    monkeypatch.setattr(video_repository, "get_connection", fake_connection)
    result = video_repository.media_statistics()

    assert result["photos"] == 2
    assert result["videos"] == 0
    assert result["today_photos"] == 0
    assert result["today_videos"] == 0
    assert result["last_photo_at"] == "2026-10-15T10:00:00"
    assert result["last_video_at"] is None
    assert len(result["months"]) == 2
    # The dynamic query substitutes an empty video relation when schema/026
    # has not yet been deployed; it must not query a missing table.
    assert not any("FROM public.video_assets" in sql for sql in connection.cursor_value.queries)
