from __future__ import annotations

import atexit
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import tempfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient


_KEY_DIRECTORY = Path(tempfile.mkdtemp(prefix="paiguangguang-test-login-key-"))
_KEY_PATH = _KEY_DIRECTORY / "private.pem"
_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_KEY_PATH.write_bytes(
    _PRIVATE_KEY.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
)
os.environ["AUTH_LOGIN_PRIVATE_KEY_PATH"] = str(_KEY_PATH)
atexit.register(shutil.rmtree, _KEY_DIRECTORY, ignore_errors=True)


def _base64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


_ORIGINAL_REQUEST = TestClient.request


def _request_with_encrypted_test_login(self, method, url, **kwargs):
    headers = dict(kwargs.get("headers") or {})
    skip_encryption = headers.pop("X-Test-Plaintext-Login", None) == "1"
    if headers:
        kwargs["headers"] = headers
    elif "headers" in kwargs:
        kwargs.pop("headers")
    body = kwargs.get("json")
    if (
        not skip_encryption
        and method.upper() == "POST"
        and str(url).endswith("/api/v1/auth/login")
        and isinstance(body, dict)
        and isinstance(body.get("password"), str)
    ):
        key_response = _ORIGINAL_REQUEST(self, "GET", "/api/v1/auth/encryption-key")
        key_response.raise_for_status()
        key_data = key_response.json()["data"]
        jwk = key_data["public_key"]
        public_key = rsa.RSAPublicNumbers(
            e=int.from_bytes(_base64url_decode(jwk["e"]), "big"),
            n=int.from_bytes(_base64url_decode(jwk["n"]), "big"),
        ).public_key()
        plaintext = json.dumps(
            {
                "password": body["password"],
                "issued_at": int(datetime.now(timezone.utc).timestamp()),
                "nonce": secrets.token_urlsafe(18),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        ciphertext = public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        kwargs["json"] = {
            "email": body["email"],
            "encrypted_password": _base64url(ciphertext),
            "key_id": key_data["key_id"],
        }
    return _ORIGINAL_REQUEST(self, method, url, **kwargs)


TestClient.request = _request_with_encrypted_test_login
