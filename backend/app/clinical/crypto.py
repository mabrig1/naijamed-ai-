import base64
import hashlib
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _decode_configured_key(raw: str) -> bytes:
    raw = raw.strip()
    if not raw:
        raise ValueError("empty key")
    try:
        padded = raw + "=" * (-len(raw) % 4)
        key = base64.urlsafe_b64decode(padded.encode())
        if len(key) == 32:
            return key
    except Exception:
        pass
    try:
        key = bytes.fromhex(raw)
        if len(key) == 32:
            return key
    except ValueError:
        pass
    raise ValueError("PHI_ENCRYPTION_KEY must decode to exactly 32 bytes (AES-256)")


def _key() -> bytes:
    if settings.PHI_ENCRYPTION_KEY:
        return _decode_configured_key(settings.PHI_ENCRYPTION_KEY)
    if settings.APP_ENV.lower() in {"production", "prod"}:
        raise RuntimeError("PHI_ENCRYPTION_KEY is required in production")
    # Development-only deterministic key so local demos remain usable.
    return hashlib.sha256((settings.SECRET_KEY + ":healthos-dev-phi").encode()).digest()


def encrypt_json(payload: dict[str, Any]) -> str:
    aes = AESGCM(_key())
    nonce = os.urandom(12)
    plaintext = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ciphertext = aes.encrypt(nonce, plaintext, b"mabrig-healthos-phi")
    return "v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt_json(token: str) -> dict[str, Any]:
    version, encoded = token.split(":", 1)
    if version != "v1":
        raise ValueError(f"Unsupported PHI encryption version: {version}")
    raw = base64.urlsafe_b64decode(encoded.encode("ascii"))
    nonce, ciphertext = raw[:12], raw[12:]
    plaintext = AESGCM(_key()).decrypt(nonce, ciphertext, b"mabrig-healthos-phi")
    return json.loads(plaintext.decode("utf-8"))
