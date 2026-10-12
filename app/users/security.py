"""
Password hashing (scrypt from the standard library, no extra dependency).

Stored format: scrypt$<salt_hex>$<hash_hex>. A NULL/empty stored value means
"no password required" (the legacy default users) — never confuse that with a
failed comparison.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

_ALGO = "scrypt"
_N = 2 ** 14
_R = 8
_P = 1
_DKLEN = 32


def hash_password(password: str) -> str:
    salt = os.urandom(16)

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
    )

    salt_hex = base64.b16encode(salt).decode("ascii")
    hash_hex = base64.b16encode(digest).decode("ascii")

    return f"{_ALGO}${salt_hex}${hash_hex}"


def verify_password(password: str, stored: str | None) -> bool:
    """True when *password* matches *stored*, or when no password is set."""

    if not stored:
        return True

    try:
        algo, salt_hex, hash_hex = stored.split("$")
    except ValueError:
        return False

    if algo != _ALGO:
        return False

    try:
        salt = base64.b16decode(salt_hex)
        expected = base64.b16decode(hash_hex)
    except (ValueError, TypeError):
        return False

    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=len(expected),
    )

    return hmac.compare_digest(digest, expected)
