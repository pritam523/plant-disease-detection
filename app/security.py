"""Dependency-free helpers for admin password hashing and signed sessions."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections import defaultdict
from typing import Any

_PBKDF2 = "pbkdf2_sha256"
_ITERATIONS = 210_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or hashlib.sha256(str(time.time_ns()).encode()).digest()[:16]
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS)
    return f"{_PBKDF2}${_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != _PBKDF2:
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(derived.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def create_session(secret: str, payload: dict[str, Any], max_age: int) -> str:
    body = dict(payload)
    body["exp"] = int(time.time()) + max_age
    encoded = _b64(json.dumps(body, separators=(",", ":")).encode("utf-8"))
    signature = _b64(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def read_session(secret: str, token: str) -> dict[str, Any] | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_unb64(encoded))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


class LoginLimiter:
    """Small in-memory throttle; sufficient for a local single-admin app."""

    def __init__(self, max_attempts: int, lock_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.lock_seconds = lock_seconds
        self._attempts: dict[str, list[float]] = defaultdict(list)

    def is_locked(self, key: str) -> bool:
        now = time.time()
        recent = [t for t in self._attempts[key] if now - t < self.lock_seconds]
        self._attempts[key] = recent
        return len(recent) >= self.max_attempts

    def record_failure(self, key: str) -> None:
        self._attempts[key].append(time.time())

    def reset(self, key: str) -> None:
        self._attempts.pop(key, None)
