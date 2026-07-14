from __future__ import annotations

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_private_key(path: Path) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the RSA key used for encrypted login payloads")
    parser.add_argument("--output", type=Path, default=Path("auth-login-private-key.pem"))
    args = parser.parse_args()
    created = generate_private_key(args.output)
    print(f"login encryption key: {'created' if created else 'already exists'} at {args.output}")


if __name__ == "__main__":
    main()
