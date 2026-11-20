"""
Уборка записей видео без файла (app/video/maintenance.py).

База не нужна: проверяется решение «файла нет» и то, какие строки попадают в
DELETE. Ошибка здесь означала бы удаление живых записей.
"""

from __future__ import annotations

import json

from app.video import maintenance


def _row(video_id, path):
    return {
        "video_id": video_id,
        "filename": video_id + ".mp4",
        "source_path": str(path) if path is not None else None,
        "parent_video_id": None,
        "display_title": None,
        "size_bytes": 1,
        "duration_seconds": 1.0,
        "created_at": "2026-11-20T10:00:00+00:00",
    }


def test_inside_ignores_sibling_with_common_prefix(tmp_path):
    """`/data/video` и `/data/video-old` — разные папки, не префикс строки."""

    video = tmp_path / "video"
    sibling = tmp_path / "video-old"
    video.mkdir()
    sibling.mkdir()

    assert maintenance.inside(str(video / "clip.mp4"), str(video)) is True
    assert maintenance.inside(str(sibling / "clip.mp4"), str(video)) is False


def test_inside_excludes_the_parent_directory(tmp_path):
    parent = tmp_path / "originals"
    parent.mkdir()

    assert maintenance.inside(str(parent / "2024" / "clip.mp4"), str(parent / "2024")) is True
    assert maintenance.inside(str(parent / "clip.mp4"), str(parent / "2024")) is False
    assert maintenance.inside(None, str(parent)) is False


def test_scope_deletes_only_missing_files_inside_the_folder(tmp_path):
    """Решает наличие файла: корень API здесь ни при чём — папку только что
    просканировали, и файл, который на диске есть, удалять нельзя."""

    folder = tmp_path / "originals"
    folder.mkdir()
    present = folder / "kept.mp4"
    present.write_bytes(b"x")
    other_folder = tmp_path / "elsewhere"
    other_folder.mkdir()
    elsewhere = other_folder / "gone.mp4"

    rows = [
        _row("VI_kept", present),
        _row("VI_gone", folder / "gone.mp4"),
        _row("VI_other", elsewhere),
        _row("VI_empty", None),
    ]

    missing = maintenance._missing_from(rows, scope=str(folder))

    assert [row["video_id"] for row in missing] == ["VI_gone"]


def test_global_mode_treats_paths_outside_roots_as_missing(tmp_path, monkeypatch):
    """Скрипт по всему реестру осторожнее: то, что не отдаётся API, не трогает
    (файл может быть жив, но вне разрешённых корней — решает человек)."""

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    inside_root = allowed / "kept.mp4"
    inside_root.write_bytes(b"x")

    outside = tmp_path / "outside"
    outside.mkdir()
    outside_file = outside / "alive.mp4"
    outside_file.write_bytes(b"x")

    roots = [str(allowed)]
    rows = [
        _row("VI_kept", inside_root),
        _row("VI_missing", allowed / "gone.mp4"),
        _row("VI_outside", outside_file),
    ]

    assert maintenance.has_file(str(outside_file), roots) is False
    missing = maintenance._missing_from(rows, roots=roots)
    assert [row["video_id"] for row in missing] == ["VI_missing", "VI_outside"]


def _fake_connection(deleted_ids, queries):
    class Cursor:
        def execute(self, sql, params=None):
            queries.append((" ".join(sql.split()), params))

        def fetchall(self):
            return [(video_id,) for video_id in deleted_ids]

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class Connection:
        def cursor(self):
            return Cursor()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    return Connection()


def test_dry_run_changes_nothing(tmp_path, monkeypatch):
    folder = tmp_path / "originals"
    folder.mkdir()
    monkeypatch.setattr(
        maintenance, "_rows", lambda: [_row("VI_gone", folder / "gone.mp4")]
    )
    monkeypatch.setattr(
        maintenance, "get_connection", lambda: (_ for _ in ()).throw(AssertionError("no writes"))
    )

    payload = maintenance.purge_missing_records(scope=folder, apply=False)

    assert payload["missing"] == 1
    assert payload["applied"] is False
    assert payload["deleted"] == 0


def test_apply_writes_a_trail_and_deletes_only_missing(tmp_path, monkeypatch):
    folder = tmp_path / "originals"
    folder.mkdir()
    present = folder / "kept.mp4"
    present.write_bytes(b"x")

    monkeypatch.setattr(
        maintenance,
        "_rows",
        lambda: [
            _row("VI_kept", present),
            _row("VI_gone", folder / "gone.mp4"),
        ],
    )
    monkeypatch.setattr(maintenance, "_derivatives", lambda ids: [{"video_id": ids[0]}])
    monkeypatch.setattr(maintenance, "REPORT_DIR", tmp_path / "reports")

    queries = []
    monkeypatch.setattr(
        maintenance,
        "get_connection",
        lambda: _fake_connection(["VI_gone"], queries),
    )

    payload = maintenance.purge_missing_records(scope=folder, apply=True)

    assert payload["deleted"] == 1
    assert queries, "DELETE must reach the database"
    sql, params = queries[-1]
    assert sql.startswith("DELETE FROM public.video_assets")
    assert params == (["VI_gone"],)

    # След сохраняется до удаления: строка и её производные.
    trail = json.loads((tmp_path / "reports" / payload["report"].split("/")[-1]).read_text())
    assert [row["video_id"] for row in trail["records"]] == ["VI_gone"]
    assert trail["derivatives"] == [{"video_id": "VI_gone"}]


def test_runner_purge_skips_missing_folder(tmp_path, monkeypatch):
    """Папки нет — ничего не трогаем и не обращаемся к базе."""

    from app.ingest import runner

    monkeypatch.setattr(
        maintenance,
        "purge_missing_records",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    summary = runner._purge_missing_videos(tmp_path / "absent")

    assert summary["removed"] == 0
    assert summary["error"]


def test_runner_purge_reports_counters(tmp_path, monkeypatch):
    from app.ingest import runner

    monkeypatch.setattr(
        maintenance,
        "purge_missing_records",
        lambda **_kwargs: {"total": 3, "missing": 2, "deleted": 2, "report": "r.json"},
    )

    summary = runner._purge_missing_videos(tmp_path)

    assert summary == {"removed": 2, "missing": 2, "report": "r.json"}
