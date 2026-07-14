from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from scripts.generate_login_key import generate_private_key


def test_generate_private_key_creates_rsa_2048_key_once(tmp_path) -> None:
    path = tmp_path / "login-private-key.pem"

    assert generate_private_key(path) is True
    original = path.read_bytes()
    assert generate_private_key(path) is False
    assert path.read_bytes() == original

    key = serialization.load_pem_private_key(original, password=None)
    assert isinstance(key, rsa.RSAPrivateKey)
    assert key.key_size == 2048


def test_database_verification_script_can_run_directly() -> None:
    backend_dir = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [sys.executable, "scripts/verify_database_initialization.py", "--help"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--env-file" in result.stdout
