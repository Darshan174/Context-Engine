"""Symmetric encryption for OAuth tokens stored in the database.

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.
The ENCRYPTION_KEY setting must be a valid Fernet key (base64-encoded 32 bytes).
Generate one with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise EncryptionError(
            "ENCRYPTION_KEY is not configured. "
            "Generate one with: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode())
    except (ValueError, Exception) as exc:
        raise EncryptionError(
            f"ENCRYPTION_KEY is malformed: {exc}. "
            "It must be a valid URL-safe base64-encoded 32-byte key."
        ) from exc


def encrypt_token(plaintext: str) -> str:
    """Encrypt a token string and return the ciphertext as a UTF-8 string."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to the original token."""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise EncryptionError("Failed to decrypt token — key may have changed") from exc
