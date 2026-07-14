from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from app.core.config import Settings
from app.schemas.auth import EncryptedLoginRequest
from app.services.login_encryption import InvalidLoginEnvelope, LoginEncryptionService
from app.storage.cache import InMemoryCacheAdapter


NOW = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _write_private_key(tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path = tmp_path / "login-private-key.pem"
    path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return private_key, path


def _service(tmp_path):
    private_key, path = _write_private_key(tmp_path)
    settings = Settings(auth_login_private_key_path=str(path), redis_url="")
    service = LoginEncryptionService(
        settings=settings,
        cache=InMemoryCacheAdapter(),
        now_provider=lambda: NOW,
    )
    return private_key, service


def _encrypted_request(private_key, service, *, password="Secret123!", issued_at=None, nonce="nonce-1234567890"):
    plaintext = json.dumps(
        {
            "password": password,
            "issued_at": int((issued_at or NOW).timestamp()),
            "nonce": nonce,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    ciphertext = private_key.public_key().encrypt(
        plaintext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return EncryptedLoginRequest(
        email="admin@example.com",
        encrypted_password=_base64url(ciphertext),
        key_id=service.get_public_key_data().key_id,
    )


def test_exports_rsa_oaep_sha256_public_jwk(tmp_path) -> None:
    _, service = _service(tmp_path)

    key_data = service.get_public_key_data()

    assert key_data.algorithm == "RSA-OAEP-256"
    assert key_data.public_key == {
        "kty": "RSA",
        "n": key_data.public_key["n"],
        "e": "AQAB",
        "alg": "RSA-OAEP-256",
        "use": "enc",
        "key_ops": ["encrypt"],
    }
    assert len(key_data.key_id) == 43


def test_decrypts_password_and_rejects_replayed_nonce(tmp_path) -> None:
    private_key, service = _service(tmp_path)
    request = _encrypted_request(private_key, service)

    assert service.decrypt_password(request) == "Secret123!"

    with pytest.raises(InvalidLoginEnvelope):
        service.decrypt_password(request)


@pytest.mark.parametrize("seconds_offset", [-61, 31])
def test_rejects_envelopes_outside_clock_window(tmp_path, seconds_offset) -> None:
    from datetime import timedelta

    private_key, service = _service(tmp_path)
    request = _encrypted_request(private_key, service, issued_at=NOW + timedelta(seconds=seconds_offset))

    with pytest.raises(InvalidLoginEnvelope):
        service.decrypt_password(request)


def test_rejects_wrong_key_and_tampered_ciphertext(tmp_path) -> None:
    private_key, service = _service(tmp_path)
    request = _encrypted_request(private_key, service)

    with pytest.raises(InvalidLoginEnvelope):
        service.decrypt_password(request.model_copy(update={"key_id": "wrong-key"}))

    raw = bytearray(base64.urlsafe_b64decode(request.encrypted_password + "=="))
    raw[-1] ^= 1
    with pytest.raises(InvalidLoginEnvelope):
        service.decrypt_password(request.model_copy(update={"encrypted_password": _base64url(bytes(raw))}))


def test_cache_add_if_absent_is_atomic_for_a_nonce() -> None:
    cache = InMemoryCacheAdapter()

    assert cache.add_if_absent("nonce", True, ttl_seconds=120) is True
    assert cache.add_if_absent("nonce", True, ttl_seconds=120) is False
