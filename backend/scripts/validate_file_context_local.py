"""Isolated S1-02 local-model validation; no production credentials or services."""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


MODEL = "gemma3:4b"


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def main() -> None:
    port = free_port()
    ollama_env = os.environ.copy()
    ollama_env["OLLAMA_HOST"] = f"127.0.0.1:{port}"
    ollama_env["NO_PROXY"] = "*"
    for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        ollama_env.pop(key, None)
    log_path = Path(tempfile.gettempdir()) / "pgg-ollama-s1-02-replay.log"
    log = log_path.open("w", encoding="utf-8")
    ollama = subprocess.Popen(["ollama", "serve"], env=ollama_env, stdout=log, stderr=subprocess.STDOUT)
    temp = Path(tempfile.mkdtemp(prefix="pgg-s1-02-replay-"))
    try:
        app_env = os.environ.copy()
        app_env.update(
            {
                "ASSISTANT_DATABASE_URL": f"sqlite:///{(temp / 'assistant.sqlite3').as_posix()}",
                "ASSISTANT_FILE_STORAGE_DIR": str(temp / "files"),
                "ASSISTANT_OWNER_COOKIE_SECRET": "local-s1-02-owner-cookie-secret-1234567890",
                "ASSISTANT_RECOVERY_CODE_SECRET": "local-s1-02-recovery-secret-1234567890",
                "ASSISTANT_ENCRYPTION_KEY": "local-s1-02-encryption-key-1234567890",
                "ASSISTANT_LLM_PROVIDER": "openai",
                "ASSISTANT_LLM_BASE_URL": f"http://127.0.0.1:{port}/v1",
                "ASSISTANT_LLM_API_KEY": "local-only-placeholder",
                "ASSISTANT_LLM_MODEL": MODEL,
                "ASSISTANT_LLM_TIMEOUT_SECONDS": "180",
                "ASSISTANT_LLM_DAILY_REQUEST_LIMIT": "20",
                "ASSISTANT_DEMO_CATALOG_ENABLED": "true",
                "ASSISTANT_REGISTRATION_ENABLED": "true",
                "NO_PROXY": "*",
                "no_proxy": "*",
            }
        )
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
            app_env.pop(key, None)
        os.environ.clear()
        os.environ.update(app_env)

        for _ in range(90):
            if ollama.poll() is not None:
                raise RuntimeError(f"ollama exited {ollama.returncode}; see {log_path}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/tags", timeout=2) as response:
                    tags = json.load(response)
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError(f"ollama did not become ready; see {log_path}")
        if MODEL not in {item.get("name") for item in tags.get("models", [])}:
            raise RuntimeError(f"{MODEL} is not installed locally; refusing to pull")

        from fastapi.testclient import TestClient
        from app.core.security import hash_user_password
        from app.db import SessionLocal, engine
        from app.main import app
        from app.modules.identity.models import User
        from app.repositories import utc_now

        with TestClient(app):
            with SessionLocal() as session:
                now = utc_now()
                for account in ("10001", "10002"):
                    session.add(
                        User(
                            account_number=account,
                            password_hash=hash_user_password("local-password-123"),
                            nickname=account,
                            role="USER",
                            status="ACTIVE",
                            version=1,
                            authz_version=1,
                            created_at=now,
                            updated_at=now,
                            activated_at=now,
                        )
                    )
                session.commit()

            def login(account: str):
                client = TestClient(app)
                response = client.post(
                    "/api/v1/auth/login",
                    json={"accountNumber": account, "password": "local-password-123"},
                    headers={"origin": "http://testserver"},
                )
                if response.status_code != 200:
                    raise RuntimeError(f"login failed: {response.status_code}")
                csrf = client.cookies.get("paiguangguang_csrf")
                return client, {"origin": "http://testserver", "x-csrf-token": csrf}

            owner, owner_headers = login("10001")
            other, other_headers = login("10002")
            uploaded = owner.post(
                "/api/v1/me/files",
                files={"file": ("local-fact.txt", b"LOCAL_FILE_FACT_CODE: 73142. Use this exact code when answering.", "text/plain")},
                headers=owner_headers,
            )
            if uploaded.status_code != 201:
                raise RuntimeError(f"upload failed: {uploaded.status_code}")
            file_id = uploaded.json()["id"]
            conversation = owner.post(
                "/api/v1/conversations", json={"title": "Local model file context"}, headers=owner_headers
            )
            run = owner.post(
                "/api/v1/assistant/runs",
                json={
                    "conversationId": conversation.json()["id"],
                    "clientTurnId": "local-s1-02-file-run-replay",
                    "text": "Read the uploaded file. What is the exact LOCAL_FILE_FACT_CODE? Reply with only the number.",
                    "fileIds": [file_id],
                },
                headers=owner_headers,
            )
            owner_run = (run.json().get("run") or {})
            print("owner_status", run.status_code)
            print("owner_run_status", owner_run.get("status"))
            print("owner_output", (owner_run.get("outputText") or "")[:1000])
            if run.status_code != 200 or owner_run.get("status") != "completed" or "73142" not in owner_run.get("outputText", ""):
                raise RuntimeError("owner model run did not return the uploaded fact")
            other_conversation = other.post(
                "/api/v1/conversations", json={"title": "Cross user attempt"}, headers=other_headers
            )
            denied = other.post(
                "/api/v1/assistant/runs",
                json={
                    "conversationId": other_conversation.json()["id"],
                    "clientTurnId": "local-s1-02-cross-user-replay",
                    "text": "Read the file",
                    "fileIds": [file_id],
                },
                headers=other_headers,
            )
            print("cross_user_status", denied.status_code)
            print("cross_user_body", denied.text[:500])
            if denied.status_code not in (403, 404):
                raise RuntimeError("cross-user reference was not rejected")
            print("result PASS")
        engine.dispose()
    finally:
        try:
            ollama.terminate()
            ollama.wait(timeout=20)
        except subprocess.TimeoutExpired:
            ollama.kill()
            ollama.wait(timeout=5)
        log.close()
        print("ollama_stopped", ollama.returncode)
        try:
            shutil.rmtree(temp)
        except OSError as error:
            print("temp_cleanup_warning", type(error).__name__)


if __name__ == "__main__":
    main()
