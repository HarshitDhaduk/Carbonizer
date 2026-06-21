"""Envelope encryption for stored provider tokens (Phase 2.8, docs/IMPROVEMENT-PLAN.md).

Why envelope, not direct symmetric — the master key (``ENCRYPTION_KEY``) lives
in process memory; rotating it shouldn't require a sweep over every row. Each
ciphertext is wrapped with Fernet (AES-128-CBC + HMAC-SHA256 + version byte),
which lets us hot-swap the master key later by re-encrypting on read.

Operational notes:
  * In production, ``ENCRYPTION_KEY`` must be set to a 32-byte url-safe
    base64 string. Generate with::

        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

  * In dev (when the env var is unset), we derive a deterministic key from the
    ``SECRET_KEY`` so the existing dev experience doesn't bifurcate. This is
    explicitly insecure and is gated behind ``is_production`` — production with
    a missing key will fail-fast in :func:`get_fernet`.
"""

from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class InsecureEncryptionKeyError(RuntimeError):
    """Raised when ENCRYPTION_KEY is missing or invalid in production."""


@lru_cache(maxsize=1)
def get_fernet() -> Fernet:
    """Return the process-wide Fernet instance.

    Cached so we don't pay key-derivation cost per call. The cache is a
    module-level singleton — tests that need to swap the key must call
    ``get_fernet.cache_clear()`` first.
    """
    key = settings.encryption_key.strip()
    if not key:
        if settings.is_production:
            raise InsecureEncryptionKeyError(
                "ENCRYPTION_KEY is required in production. Generate one with "
                "`Fernet.generate_key()` and set it in the environment."
            )
        # Derive a stable dev key from SECRET_KEY so restarts decrypt prior
        # writes. This MUST NOT be reached in production (gated above).
        digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest).decode("ascii")
    try:
        return Fernet(key.encode("ascii") if isinstance(key, str) else key)
    except (ValueError, TypeError) as exc:
        raise InsecureEncryptionKeyError(
            "ENCRYPTION_KEY is not a valid Fernet key (32-byte url-safe base64)."
        ) from exc


def encrypt(plaintext: str) -> bytes:
    """Encrypt a string. Returns ciphertext bytes for storage in a BYTEA column."""
    return get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt(ciphertext: bytes | memoryview | None) -> str | None:
    """Decrypt a ciphertext blob. Returns None if input is None.

    Raises :class:`InvalidToken` if the ciphertext was produced with a different
    key — that's the signal to rotate or roll forward. Callers should handle
    this by re-reading from the source rather than crashing the request.
    """
    if ciphertext is None:
        return None
    blob = bytes(ciphertext) if isinstance(ciphertext, memoryview) else ciphertext
    try:
        return get_fernet().decrypt(blob).decode("utf-8")
    except InvalidToken:
        # Re-raise so callers know the row needs re-encryption — silently
        # returning None would mask a key-rotation bug.
        raise
