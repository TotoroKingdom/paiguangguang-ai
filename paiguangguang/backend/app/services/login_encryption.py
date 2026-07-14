from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import Settings, get_settings
from app.schemas.auth import EncryptedLoginRequest, LoginEncryptionKeyData
from app.storage.cache import CacheAdapter, get_cache_adapter


_NONCE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{16,128}$")
_MAX_AGE_SECONDS = 60
_MAX_FUTURE_SECONDS = 30
_NONCE_TTL_SECONDS = 120


class InvalidLoginEnvelope(ValueError):
    """Raised when an encrypted login credential cannot be trusted."""


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    if not value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise InvalidLoginEnvelope("Invalid encrypted credential")
    try:
        return base64.b64decode(
            value + "=" * (-len(value) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (ValueError, TypeError) as exc:
        raise InvalidLoginEnvelope("Invalid encrypted credential") from exc


class LoginEncryptionService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        cache: CacheAdapter | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cache = cache or get_cache_adapter(self.settings)
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        key_path = Path(self.settings.auth_login_private_key_path)
        try:
            loaded_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        except (OSError, ValueError, TypeError) as exc:
            raise RuntimeError(f"Unable to load login encryption key from {key_path}") from exc
        if not isinstance(loaded_key, rsa.RSAPrivateKey) or loaded_key.key_size < 2048:
            raise RuntimeError("Login encryption key must be an RSA private key of at least 2048 bits")
        self._private_key = loaded_key
        self._public_key_data = self._build_public_key_data()

    def _build_public_key_data(self) -> LoginEncryptionKeyData:
        public_key = self._private_key.public_key()
        numbers = public_key.public_numbers()
        modulus = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
        exponent = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
        fingerprint_source = public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return LoginEncryptionKeyData(
            key_id=_base64url(sha256(fingerprint_source).digest()),
            public_key={
                "kty": "RSA",
                "n": _base64url(modulus),
                "e": _base64url(exponent),
                "alg": "RSA-OAEP-256",
                "use": "enc",
                "key_ops": ["encrypt"],
            },
        )

    def get_public_key_data(self) -> LoginEncryptionKeyData:
        return self._public_key_data

    def decrypt_password(self, request: EncryptedLoginRequest) -> str:
        if request.key_id != self._public_key_data.key_id:
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        try:
            plaintext = self._private_key.decrypt(
                _base64url_decode(request.encrypted_password),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            payload = json.loads(plaintext.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InvalidLoginEnvelope("Invalid encrypted credential") from exc
        if not isinstance(payload, dict) or set(payload) != {"password", "issued_at", "nonce"}:
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        password = payload.get("password")
        issued_at = payload.get("issued_at")
        nonce = payload.get("nonce")
        if not isinstance(password, str) or not 1 <= len(password) <= 256:
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        if isinstance(issued_at, bool) or not isinstance(issued_at, int):
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        if not isinstance(nonce, str) or not _NONCE_PATTERN.fullmatch(nonce):
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        now_timestamp = int(self.now_provider().timestamp())
        age = now_timestamp - issued_at
        if age > _MAX_AGE_SECONDS or age < -_MAX_FUTURE_SECONDS:
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        nonce_key = f"auth:login-nonce:{request.key_id}:{nonce}"
        if not self.cache.add_if_absent(nonce_key, True, ttl_seconds=_NONCE_TTL_SECONDS):
            raise InvalidLoginEnvelope("Invalid encrypted credential")
        return password


_LOGIN_ENCRYPTION_SERVICE: LoginEncryptionService | None = None


def get_login_encryption_service() -> LoginEncryptionService:
    global _LOGIN_ENCRYPTION_SERVICE
    if _LOGIN_ENCRYPTION_SERVICE is None:
        _LOGIN_ENCRYPTION_SERVICE = LoginEncryptionService()
    return _LOGIN_ENCRYPTION_SERVICE
