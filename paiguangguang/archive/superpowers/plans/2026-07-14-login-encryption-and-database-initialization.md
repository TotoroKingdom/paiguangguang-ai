# Login Encryption and Database Initialization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialize and verify the configured database and ensure login HTTP requests contain only an RSA-OAEP encrypted password envelope.

**Architecture:** A focused backend encryption service loads an RSA private key, publishes its JWK, decrypts and validates short-lived replay-protected envelopes, and passes only the recovered password to the existing authentication service. A focused frontend module uses Web Crypto to fetch/import the public key and build the encrypted request before using the existing API client.

**Tech Stack:** FastAPI, Pydantic, cryptography, Redis/in-memory cache, Next.js, TypeScript, Web Crypto, pytest, Vitest, Alembic, SQLAlchemy.

## Global Constraints

- HTTPS remains required; application encryption does not replace TLS.
- The login request body must not contain a `password` property or plaintext password.
- Plaintext login requests must fail schema validation.
- Envelopes expire after 60 seconds, tolerate at most 30 seconds of future clock skew, and nonces remain consumed for 120 seconds.
- Existing API-key configuration remains unchanged.
- Existing user password hashes remain PBKDF2-SHA256.

---

### Task 1: Backend credential envelope and replay protection

**Files:**
- Create: `backend/app/services/login_encryption.py`
- Create: `backend/tests/test_login_encryption.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/storage/cache.py`
- Modify: `backend/requirements.txt`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `Settings`, `CacheAdapter`.
- Produces: `LoginEncryptionService.get_public_key_data()` and `LoginEncryptionService.decrypt_password(request)`; `get_login_encryption_service()` dependency; `CacheAdapter.add_if_absent(key, value, ttl_seconds) -> bool`.

- [ ] **Step 1: Write failing service tests**

Generate an RSA test key and assert JWK export, successful OAEP/SHA-256 decryption, rejected wrong key IDs, tampering, expired/future timestamps, malformed payloads, and repeated nonces.

- [ ] **Step 2: Verify the tests fail for the missing service**

Run: `uv run pytest backend/tests/test_login_encryption.py -q`

Expected: collection fails because `app.services.login_encryption` does not exist.

- [ ] **Step 3: Implement atomic nonce insertion and the encryption service**

Add an in-memory locked check-and-set and Redis `SET key value NX EX ttl`. Load a PEM RSA private key with `serialization.load_pem_private_key`, export modulus/exponent as base64url JWK, use a SHA-256 DER public-key fingerprint as `key_id`, decrypt with `OAEP(MGF1(SHA256), SHA256)`, validate JSON/timestamp/nonce/password, then atomically consume the nonce.

- [ ] **Step 4: Run focused backend service tests**

Run: `uv run pytest backend/tests/test_login_encryption.py -q`

Expected: all tests pass.

### Task 2: Encrypted auth API

**Files:**
- Modify: `backend/app/api/v1/auth.py`
- Modify: `backend/app/services/auth.py`
- Modify: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `LoginEncryptionService.decrypt_password` and encrypted `LoginRequest` fields.
- Produces: `GET /api/v1/auth/encryption-key`; encrypted-only `POST /api/v1/auth/login`.

- [ ] **Step 1: Convert auth API tests to encrypted login and add plaintext rejection**

Override `get_login_encryption_service`, encrypt test envelopes with the generated public key, assert a valid encrypted login returns a token, wrong encrypted passwords return 401, plaintext `{password: ...}` returns 422, and a repeated encrypted request returns 401.

- [ ] **Step 2: Verify tests fail against the plaintext API**

Run: `uv run pytest backend/tests/test_auth.py -q`

Expected: encryption-key route is missing and encrypted login is rejected.

- [ ] **Step 3: Wire the service into the router**

Return `ApiResponse[LoginEncryptionKeyData]` from the public-key endpoint. Decrypt inside the login route and call `AuthService.login_with_password(session, email, password)`. Map all credential-envelope validation failures to the existing generic HTTP 401 response.

- [ ] **Step 4: Verify backend auth tests**

Run: `uv run pytest backend/tests/test_auth.py backend/tests/test_login_encryption.py -q`

Expected: all tests pass.

### Task 3: Frontend Web Crypto request

**Files:**
- Create: `frontend/lib/login-encryption.ts`
- Create: `frontend/lib/login-encryption.test.ts`
- Modify: `frontend/types/auth.ts`
- Modify: `frontend/lib/auth.ts`
- Create: `frontend/lib/auth.test.ts`

**Interfaces:**
- Consumes: public JWK returned by `/api/v1/auth/encryption-key`, `window.crypto.subtle`, and existing `getJson`/`postJson`.
- Produces: `encryptLoginPassword(password, keyData)` and `login({email, password})` that submits `{email, encrypted_password, key_id}`.

- [ ] **Step 1: Write failing frontend encryption and request-shape tests**

Assert UTF-8 envelope construction, cryptographically random base64url nonce generation, RSA-OAEP/SHA-256 import/encryption calls, and that the body passed to `postJson` has no `password` property or plaintext value.

- [ ] **Step 2: Verify frontend tests fail**

Run: `npm test -- --run lib/login-encryption.test.ts lib/auth.test.ts` from `frontend`.

Expected: missing module/functions cause test failure.

- [ ] **Step 3: Implement the minimal Web Crypto module and login orchestration**

Fetch the public key, import it with `{name: "RSA-OAEP", hash: "SHA-256"}`, serialize `{password, issued_at, nonce}`, encrypt it, base64url encode the ciphertext, and submit only the encrypted body. Throw an explicit unsupported-browser error when Web Crypto is unavailable; never fall back to plaintext.

- [ ] **Step 4: Verify focused frontend tests**

Run: `npm test -- --run lib/login-encryption.test.ts lib/auth.test.ts` from `frontend`.

Expected: all focused tests pass.

### Task 4: Key provisioning and database initialization

**Files:**
- Create locally, ignored by Git: `backend/auth-login-private-key.pem`
- Create: `backend/scripts/generate_login_key.py`
- Create: `backend/scripts/verify_database_initialization.py`
- Modify: `backend/dev.env`
- Modify: `backend/prod.env`
- Modify: `.gitignore`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`

**Interfaces:**
- Consumes: `AUTH_LOGIN_PRIVATE_KEY_PATH`, existing database/admin settings, Alembic and bootstrap services.
- Produces: persistent local RSA private key and a secret-safe database verification report.

- [ ] **Step 1: Add tests for configuration and idempotent database verification behavior**

Extend configuration/database tests to assert the key path loads and bootstrap remains idempotent with a PBKDF2-SHA256 administrator hash.

- [ ] **Step 2: Verify the configuration test fails**

Run: `uv run pytest backend/tests/test_database_setup.py -q`

Expected: settings have no `auth_login_private_key_path`.

- [ ] **Step 3: Add key generation and database verification scripts**

The key generator creates an RSA-2048 PKCS8 PEM with restrictive file permissions when absent. The verification script runs `initialize_database()` twice, compares Alembic current heads with script heads, and verifies administrator/RBAC/workspace/hash state without printing credentials.

- [ ] **Step 4: Provision key and initialize the configured database**

Run from `backend`:

```powershell
uv run python scripts/generate_login_key.py --output auth-login-private-key.pem
uv run python scripts/verify_database_initialization.py --env-file dev.env
```

Expected: key exists, migration head is `0007`, two initialization passes succeed, and administrator verification reports `pbkdf2_sha256`.

### Task 5: Full verification

**Files:**
- Modify only files required to resolve regressions caused by Tasks 1-4.

**Interfaces:**
- Consumes: completed backend/frontend implementation.
- Produces: verification evidence.

- [ ] **Step 1: Run backend tests**

Run: `uv run pytest backend/tests -q`

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests**

Run from `frontend`: `npm test`

Expected: all tests pass.

- [ ] **Step 3: Run frontend build**

Run from `frontend`: `npm run build`

Expected: production build completes.

- [ ] **Step 4: Inspect the login payload contract**

Run the encrypted login integration test and verify the captured request JSON contains exactly `email`, `encrypted_password`, and `key_id`, with no plaintext password.
