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

import os

from fastapi import Header, HTTPException

# Role -> scopes. Администратор can do anything.
ROLE_SCOPES: dict[str, set[str]] = {
    "Администратор": {"*"},
    "Менеджер": {
        "read",
        "collections:write",
        "searches:write",
        "upload:write",
        "jobs:read",
    },
    "Гость": {"read"},
}


def _token_scopes() -> dict[str, set[str]]:
    raw = os.getenv("SCENE_API_TOKENS", "").strip()

    tokens: dict[str, set[str]] = {}

    if not raw:
        return tokens

    for entry in raw.split(","):
        entry = entry.strip()

        if not entry:
            continue

        token, _, scopes = entry.partition(":")
        token = token.strip()

        if token:
            tokens[token] = {
                scope.strip()
                for scope in scopes.split("|")
                if scope.strip()
            }

    return tokens


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

    # Fall back to a user session token.
    from app.users import database as users_db

    user = users_db.get_session(token)

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
