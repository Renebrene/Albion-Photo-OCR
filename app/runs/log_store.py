"""Private filesystem store for bounded, redacted run logs."""

from __future__ import annotations

import os
import re
import stat
import tempfile
import time
from pathlib import Path

from app.core.errors import redact_absolute_paths

LOG_ROOT = Path(os.getenv("SCENE_RUN_LOG_ROOT", "data/logs")).expanduser()
LOG_RETENTION_SECONDS = 30 * 24 * 60 * 60
MAX_LOG_BYTES = int(os.getenv("SCENE_RUN_LOG_MAX_BYTES", str(2 * 1024 * 1024)))
_SAFE_KIND = re.compile(r"[^a-z0-9_-]+")


def _kind(kind: str) -> str:
    cleaned = _SAFE_KIND.sub("_", str(kind).lower()).strip("_")
    return cleaned[:40] or "run"


def _log_path(run_id: int, kind: str) -> Path:
    # The filename is derived only from a DB-generated integer and a small
    # allowlisted/normalised kind; never from a client-supplied path.
    return LOG_ROOT / f"{int(run_id)}-{_kind(kind)}.log"


def _redact(text: object) -> str:
    value = redact_absolute_paths(str(text or ""))
    # Do not persist bearer credentials or common API-key header forms.
    value = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
        r"\1[REDACTED]",
        value,
    )
    value = re.sub(
        r"(?i)((?:api[_-]?key|token)\s*[=:]\s*)[^\s,;]+",
        r"\1[REDACTED]",
        value,
    )
    return value


def _bounded(lines: list[str]) -> str:
    body = "\n".join(_redact(line) for line in lines if line is not None)
    if len(body.encode("utf-8")) <= MAX_LOG_BYTES:
        return body + ("\n" if body else "")
    tail = body.encode("utf-8")[-MAX_LOG_BYTES:]
    # Trim a possible partial UTF-8 codepoint at the front.
    return "[log truncated]\n" + tail.decode("utf-8", errors="ignore")


def append_lines(run_id: int, kind: str, lines: list[str]) -> str:
    """Append redacted events to a run log; return the safe relative path."""

    target = _log_path(run_id, kind)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Files are private (mode 0600). Use a generated path, O_APPEND and no
    # symlink-following where the platform supports it.
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        os.fchmod(fd, 0o600)
        current = os.fstat(fd).st_size
        remaining = max(0, MAX_LOG_BYTES - current)
        encoded = _bounded(lines).encode("utf-8")
        if remaining:
            os.write(fd, encoded[:remaining])
        if len(encoded) > remaining and remaining > 32:
            os.write(fd, b"\n[log truncated]\n")
    finally:
        os.close(fd)

    return f"{int(run_id)}-{_kind(kind)}.log"


def publish_lines(run_id: int, kind: str, lines: list[str]) -> str:
    """Atomically replace a run log with a bounded, redacted snapshot."""

    target = _log_path(run_id, kind)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temp_name = tempfile.mkstemp(prefix=".tmp-run-log-", dir=target.parent)
    temp = Path(temp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(_bounded(lines))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
        os.chmod(target, 0o600)
    except Exception:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    return f"{int(run_id)}-{_kind(kind)}.log"


def read_log(relative_path: str) -> str | None:
    """Read only a generated relative log path contained in LOG_ROOT."""

    if not relative_path or Path(relative_path).is_absolute():
        return None
    if Path(relative_path).name != relative_path or ".." in Path(relative_path).parts:
        return None

    try:
        root = LOG_ROOT.resolve(strict=True)
        candidate = root / relative_path
        if candidate.is_symlink():
            return None
        target = candidate.resolve(strict=True)
        target.relative_to(root)
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(target, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                return None
            with os.fdopen(fd, "rb") as stream:
                data = stream.read(MAX_LOG_BYTES)
        finally:
            try:
                os.close(fd)
            except OSError:
                pass
    except (OSError, RuntimeError, ValueError):
        return None

    return data.decode("utf-8", errors="replace")


def prune_stale(*, now: float | None = None) -> int:
    """Remove only regular, non-symlink logs older than the 30-day retention."""

    if not LOG_ROOT.is_dir():
        return 0

    deadline = (time.time() if now is None else float(now)) - LOG_RETENTION_SECONDS
    removed = 0
    for entry in LOG_ROOT.iterdir():
        try:
            if entry.name.startswith(".") or entry.is_symlink() or not entry.is_file():
                continue
            if entry.suffix != ".log":
                continue
            if entry.stat().st_mtime < deadline:
                entry.unlink()
                removed += 1
        except OSError:
            continue
    return removed
