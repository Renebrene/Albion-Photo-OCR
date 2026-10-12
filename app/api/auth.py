"""
Optional bearer-token authentication with simple scopes.

Behaviour:
  * If SCENE_API_TOKENS is unset/empty, authentication is DISABLED and every
    request is allowed. This keeps local development friction-free.
  * If it is set, read endpoints require scope "read" and the original-file
    endpoint requires scope "originals". Scope "*" grants everything.

Format (comma-separated entries, scopes joined by "|"):
    SCENE_API_TOKENS="devtoken:read,secret:read|originals,admin:*"

This is a self-hosted stopping point; an OIDC/OAuth2 provider can replace
this dependency later without touching the endpoints.
"""

from __future__ import annotations

import os

from fastapi import Header, HTTPException


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


def auth_enabled() -> bool:
    return bool(_token_scopes())


def require_scope(scope: str):
    """Return a FastAPI dependency enforcing *scope* when auth is enabled."""

    def dependency(authorization: str | None = Header(default=None)):
        tokens = _token_scopes()

        if not tokens:
            return None  # authentication disabled

        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=401,
                detail="missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = authorization.split(" ", 1)[1].strip()
        scopes = tokens.get(token)

        if scopes is None:
            raise HTTPException(
                status_code=401,
                detail="invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if "*" not in scopes and scope not in scopes:
            raise HTTPException(status_code=403, detail="insufficient scope")

        return token

    return dependency
