"""
Symmetric encryption for sensitive values (API keys, tokens).
Uses Fernet (AES-128-CBC with HMAC-SHA256) from the `cryptography` package.

Encryption key source (in priority order):
  1. ENCRYPTION_KEY env var (raw 32-byte base64-encoded key)
  2. Derived from FLASK_SECRET_KEY via PBKDF2

Usage:
    from crypto_utils import encrypt_value, decrypt_value
    cipher = encrypt_value("sk-ant-abc123")   # -> "gAAAAA…"
    plain  = decrypt_value(cipher)            # -> "sk-ant-abc123"
"""

import os
import base64
import hashlib
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

logger = logging.getLogger(__name__)

# Read salt from env var; fall back to a legacy default but warn loudly
_SALT_ENV = os.getenv("ENCRYPTION_SALT", "").strip()
if _SALT_ENV:
    _SALT = _SALT_ENV.encode("utf-8")
else:
    _SALT = b"velank-api-key-encryption-salt-v1"
    logger.warning(
        "ENCRYPTION_SALT env var is not set — using legacy hardcoded salt. "
        "Set ENCRYPTION_SALT to a unique random string for production."
    )

_fernet_instance: Optional[Fernet] = None


def _derive_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from an arbitrary secret string."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret.encode("utf-8")))


def _get_fernet() -> Fernet:
    """Return a cached Fernet instance (created once)."""
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    explicit_key = (os.getenv("ENCRYPTION_KEY") or "").strip()
    if explicit_key:
        # If the user supplies a ready-made Fernet key, use it directly
        try:
            _fernet_instance = Fernet(explicit_key.encode("utf-8"))
            return _fernet_instance
        except Exception:
            pass
        # Fall back to deriving from it
        _fernet_instance = Fernet(_derive_key(explicit_key))
        return _fernet_instance

    flask_secret = os.getenv("FLASK_SECRET_KEY", "").strip()
    if not flask_secret:
        raise RuntimeError(
            "Neither ENCRYPTION_KEY nor FLASK_SECRET_KEY is set. "
            "Cannot initialise encryption. Set one of these env vars."
        )
    _fernet_instance = Fernet(_derive_key(flask_secret))
    return _fernet_instance


# ── Public API ────────────────────────────────────────────────────────────

_ENCRYPTED_PREFIX = "enc::"


def is_encrypted(value: str) -> bool:
    """Check whether a string is already in encrypted form."""
    return isinstance(value, str) and value.startswith(_ENCRYPTED_PREFIX)


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string.  Returns prefixed ciphertext.

    Returns the original value unchanged if it is empty or already encrypted.
    """
    if not plaintext or is_encrypted(plaintext):
        return plaintext
    try:
        f = _get_fernet()
        token = f.encrypt(plaintext.encode("utf-8"))
        return _ENCRYPTED_PREFIX + token.decode("utf-8")
    except Exception as exc:
        logger.error("Encryption failed: %s", exc)
        raise RuntimeError(f"Failed to encrypt sensitive value: {exc}") from exc


def decrypt_value(ciphertext: str) -> str:
    """Decrypt an ``enc::``-prefixed ciphertext.

    - If the value is not encrypted (no prefix), return as-is.
    - If decryption fails (wrong key), return empty string and log a warning.
    """
    if not ciphertext or not is_encrypted(ciphertext):
        return ciphertext  # not encrypted — pass through
    raw_token = ciphertext[len(_ENCRYPTED_PREFIX):]
    try:
        f = _get_fernet()
        return f.decrypt(raw_token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.warning("Decryption failed (invalid token / wrong key). Returning empty.")
        return ""
    except Exception as exc:
        logger.error("Decryption error: %s", exc)
        return ""
