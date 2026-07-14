# Login Encryption and Database Initialization Design

## Scope

This change initializes the configured application database and replaces the plaintext password field in the login HTTP payload with an RSA-OAEP encrypted credential envelope. Existing API keys and other pre-existing secret configuration are explicitly outside this change.

The browser Network panel must not show the plaintext password in the login request. This requirement does not claim that a user controlling the browser cannot inspect the password input, React state, JavaScript execution, or process memory. HTTPS remains mandatory because application-layer password encryption does not protect the rest of the session or replace TLS.

## Database Initialization

The existing `initialize_database` workflow remains authoritative:

1. Resolve the configured database URL.
2. Apply Alembic migrations through the latest revision.
3. Bootstrap default RBAC roles, permissions, and the default workspace.
4. Create or update the configured administrator.
5. Verify that the administrator exists, is active, has the `system_admin` role, belongs to the default workspace, and has a PBKDF2-SHA256 password hash rather than a plaintext password.

Initialization must be idempotent. Running it twice must not create duplicate users, roles, permissions, or memberships.

## Credential Encryption Architecture

The backend owns an RSA-2048 key pair used only for login credential transport. The private key is loaded from a path configured through `AUTH_LOGIN_PRIVATE_KEY_PATH`; it is never sent to the frontend. A generated development key is stored outside Git, while deployments must mount their own private key. The backend derives the public key and exposes it as a JWK.

The frontend requests the current public key from `GET /api/v1/auth/encryption-key`, imports it with the Web Crypto API, and encrypts a UTF-8 JSON plaintext using RSA-OAEP with SHA-256. The plaintext contains:

```json
{
  "password": "the user-entered password",
  "issued_at": 1784044800,
  "nonce": "a cryptographically random base64url value"
}
```

The login request becomes:

```json
{
  "email": "admin@example.com",
  "encrypted_password": "base64url RSA-OAEP ciphertext",
  "key_id": "SHA-256 public-key fingerprint"
}
```

No plaintext password property is serialized into the login request.

## Backend Components

`LoginEncryptionService` is responsible for loading and validating the RSA private key, exporting the public JWK, deriving `key_id`, decrypting envelopes, validating timestamps, and consuming nonces. It exposes a small interface independent from authentication:

- `get_public_key_data() -> LoginEncryptionKeyData`
- `decrypt_password(request: EncryptedLoginRequest) -> str`

The service rejects:

- unknown key identifiers;
- invalid base64url or malformed ciphertext;
- ciphertext that cannot be decrypted with RSA-OAEP/SHA-256;
- plaintext that is not the expected JSON shape;
- timestamps more than 60 seconds old or more than 30 seconds in the future;
- missing, malformed, or previously consumed nonces;
- passwords outside the existing 1-to-256 character constraint.

Consumed nonces are stored in the configured cache for 120 seconds. Redis provides cross-process replay protection in deployed environments; the existing in-memory cache is the development fallback. Authentication failures continue to use a generic message and must not reveal whether decryption, user lookup, or password verification failed.

The auth router obtains the encryption service through dependency injection. `POST /api/v1/auth/login` decrypts the password and passes it to the existing password verification path without persisting or logging the plaintext.

## Frontend Components

A focused frontend encryption module performs public-key retrieval, JWK import, nonce creation, envelope serialization, RSA-OAEP encryption, and base64url encoding. The existing `login` API function calls this module before invoking `postJson`.

The public key may be cached in memory for the page lifetime. When login fails because the key identifier is no longer current, the frontend clears the cached key, fetches it once more, and retries encryption once. It never retries an authentication failure.

Browsers without the required Web Crypto APIs receive an explicit message that secure login is unsupported. The frontend must not fall back to plaintext submission.

## Error Handling

Public API errors use the existing response envelope. Invalid encrypted credentials return HTTP 401 with the same generic `Invalid email or password` response as an incorrect password. Missing server key configuration is a startup/configuration failure and must be logged without key contents.

The frontend differentiates unsupported-browser, network, timeout, and authentication errors for the user, while never including password material in errors or logs.

## Testing

Backend tests cover public JWK export, successful encryption/decryption, wrong key IDs, tampered ciphertext, expired/future timestamps, replayed nonces, and successful/failed login through the HTTP API. Tests generate an isolated RSA key and use a temporary SQLite database.

Frontend tests cover Web Crypto encryption output, absence of a plaintext `password` field in the submitted body, public-key refresh after key rotation, unsupported Web Crypto behavior, and login UI error handling.

Database verification records migration head, user/RBAC/workspace counts, administrator state, and the password-hash scheme without printing any configured password or secret.

## Acceptance Criteria

- The configured database is at the latest Alembic revision and bootstrap verification passes twice.
- A valid encrypted login returns a JWT and `/api/v1/auth/me` returns the authenticated user.
- The login Network request body contains no plaintext password or `password` field.
- Plaintext password login requests are rejected by schema validation.
- Replaying the same encrypted payload is rejected.
- Existing backend and frontend test suites remain green.
- Existing API-key configuration is left unchanged.
