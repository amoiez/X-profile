"""Username validation and normalization for X handles.

X usernames are 1-15 characters, letters/digits/underscore only. We accept an
optional leading '@' and normalize it away.
"""

from __future__ import annotations

import re

from app.core.errors import AppError, ErrorCode

_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{1,15}$")


def normalize_username(raw: str) -> str:
    """Validate and normalize an X username, or raise INVALID_USERNAME."""
    if raw is None:
        raise AppError(ErrorCode.INVALID_USERNAME)
    candidate = raw.strip()
    if candidate.startswith("@"):
        candidate = candidate[1:]
    candidate = candidate.strip()
    if not _USERNAME_RE.match(candidate):
        raise AppError(
            ErrorCode.INVALID_USERNAME,
            "Username must be 1-15 characters: letters, digits, or underscores.",
        )
    return candidate
