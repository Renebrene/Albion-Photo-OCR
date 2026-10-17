"""
Authentication: optional service tokens plus user sessions.

Two credential kinds are accepted as `Authorization: Bearer <token>`:
  * a service token from SCENE_API_TOKENS (scope list, "*" = all);
  * a user session token (app.users.database) — scope comes from the role.

Enforcement is ON by default (fail-closed). Set SCENE_AUTH_REQUIRED=0 to open
the API for local development; a valid session token is still honoured, and
/auth endpoints still work either way.

Scope format of SCENE_API_TOKENS: `token:scope1|scope2`, comma separated.
"""

from __future__ import annotations

import logging
import os

from fastapi import Header, HTTPException

logger = logging.getLogger(__name__)

# Cache for the validated SCENE_API_TOKENS parse.
_tokens_cache_raw: str | None = None
_tokens_cache_value: dict[str, set[str]] = {}

# Role -> scopes. Администратор can do anything.
ROLE_SCOPES: dict[str, set[str]] = {
    "Администратор": {"*"},
    "Менеджер": {
        "read",
        "collections:write",
        "searches:write",
        "upload:write",
        # Manual corrections of the QWEN description in the photo card.
        "photos:write",
        # Working pipeline jobs (INGEST, DINO/HYBRID/QWEN, pause/cancel,
        # fingerprint builds) are day-to-day operation, not administration:
        # the manager may run and steer them (owner decision 2026-10-16).
        # QWEN provider/model/API-key changes use the separate, admin-only
        # `settings:write` scope.
        "jobs:read",
        "jobs:write",
        # Names for the addresses (schema/022) are day-to-day curation work,
        # not administration: the manager may edit them.
        "addresses:write",
        # Downloading. The manager differs from the administrator only by the
        # technical section, so he downloads video derivatives AND photo
        # originals (owner decision 2026-10-16). The only role kept away from
        # downloads is Гость: tests/test_video_api.py pins that it has neither
        # the video scopes nor `originals`.
        "videos:read",
        "videos:write",
        "videos:download",
        "originals",
    },
    "Гость": {"read"},
}


def parse_tokens(raw: str) -> dict[str, set[str]]:
    """
    Parse SCENE_API_TOKENS into {token: scopes}.

    Format: ``token:scope1|scope2, token2:scope3`` ("*" = all scopes).

    Raises ValueError on a malformed entry (no colon, empty token, empty scope
    list, or a duplicate token), so a typo cannot silently weaken access
    control.
    """

    tokens: dict[str, set[str]] = {}

    for entry in (raw or "").split(","):
        entry = entry.strip()

        if not entry:
            continue

        token, sep, scopes = entry.partition(":")
        token = token.strip()

        if not sep:
            raise ValueError(
                f"SCENE_API_TOKENS entry {entry!r} has no ':scopes' part"
            )

        if not token:
            raise ValueError("SCENE_API_TOKENS has an entry with an empty token")

        parsed = {scope.strip() for scope in scopes.split("|") if scope.strip()}

        if not parsed:
            raise ValueError(
                f"SCENE_API_TOKENS token {token!r} has no scopes"
            )

        if token in tokens:
            raise ValueError(f"SCENE_API_TOKENS defines token {token!r} twice")

        tokens[token] = parsed

    return tokens


def _token_scopes() -> dict[str, set[str]]:
    """
    Cached, validated parse of SCENE_API_TOKENS.

    An invalid configuration raises (fail-closed): requests fail loudly rather
    than running with a partially applied access policy.
    """

    raw = os.getenv("SCENE_API_TOKENS", "").strip()

    global _tokens_cache_raw, _tokens_cache_value

    if raw == _tokens_cache_raw:
        return _tokens_cache_value

    try:
        parsed = parse_tokens(raw)
    except ValueError as exc:
        raise RuntimeError(f"invalid SCENE_API_TOKENS: {exc}") from exc

    _tokens_cache_raw = raw
    _tokens_cache_value = parsed

    return parsed


def _forced() -> bool:
    """
    Fail-closed: authentication is required unless explicitly disabled.

    SCENE_AUTH_REQUIRED defaults to "1" (enforced). Set it to "0"/"false"/
    "no" only for trusted local development.
    """

    return os.getenv("SCENE_AUTH_REQUIRED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def validate_token_config() -> None:
    """
    Validate SCENE_API_TOKENS at startup; raises RuntimeError when malformed.

    Called from the app factory so a typo fails the boot instead of weakening
    access control at request time.
    """

    _token_scopes()


def auth_enabled() -> bool:
    return bool(_token_scopes()) or _forced()


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def resolve_principal(authorization: str | None) -> dict | None:
    """
    Resolve a bearer credential into a principal, or None when invalid.

    Returns {"kind": "service"|"user", "scopes": set, "user": dict|None}.
    """

    token = _bearer_token(authorization)

    if not token:
        return None

    scopes = _token_scopes().get(token)

    if scopes is not None:
        return {"kind": "service", "scopes": scopes, "user": None}

    # Fall back to a user session token. A database that is unreachable or not
    # configured must never turn an unauthenticated request into a 500: we fail
    # closed and treat the credential as invalid, so the caller answers 401.
    from app.users import database as users_db

    try:
        user = users_db.get_session(token)
    except Exception as exc:  # noqa: BLE001 - any failure means "cannot verify"
        logger.warning(
            "session lookup failed (%s); treating bearer token as invalid",
            type(exc).__name__,
        )
        return None

    if user is None:
        return None

    return {
        "kind": "user",
        "scopes": set(ROLE_SCOPES.get(user["role"], {"read"})),
        "user": user,
    }


def require_scope(scope: str):
    """FastAPI dependency enforcing *scope* when authentication is enabled."""

    def dependency(authorization: str | None = Header(default=None)):
        if not auth_enabled():
            # Open mode: a valid session is still reported when provided.
            return resolve_principal(authorization)

        principal = resolve_principal(authorization)

        if principal is None:
            raise HTTPException(
                status_code=401,
                detail="missing or invalid credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        scopes = principal["scopes"]

        if "*" not in scopes and scope not in scopes:
            raise HTTPException(status_code=403, detail="insufficient scope")

        return principal

    return dependency
