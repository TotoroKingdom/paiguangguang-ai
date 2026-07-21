# GHCR Single-Server Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy Paiguangguang automatically to `http://1.12.47.29:8080` through the existing Nginx container, using immutable frontend/backend images published to GHCR by GitHub Actions.

**Architecture:** GitHub Actions validates both applications, builds two commit-SHA-tagged images, pushes them to GHCR, then invokes a server-side deployment script over SSH. Nginx, frontend, and backend share an external `web` network; Redis is isolated on `app_internal`; Neon provides PostgreSQL; Redis and Chroma use persistent named volumes.

**Tech Stack:** GitHub Actions, GHCR, Docker Buildx, Docker Compose v2, Next.js 14, Node.js 20, FastAPI, Python 3.12, Redis 7, Neon PostgreSQL, Chroma, Nginx.

## Global Constraints

- The public test entry point is exactly `http://1.12.47.29:8080`.
- Browser API requests must use same-origin paths such as `/api/v1/health`; production bundles must not contain `localhost` or `127.0.0.1` as the API base.
- The production server builds no application source; it pulls `ghcr.io/totorokingdom/paiguangguang-frontend:${IMAGE_TAG}` and `ghcr.io/totorokingdom/paiguangguang-backend:${IMAGE_TAG}`.
- `IMAGE_TAG` is the full Git commit SHA and is immutable for deployments.
- Only Nginx exposes a host port. Frontend port 3000, backend port 8000, and Redis port 6379 remain Docker-internal.
- PostgreSQL is Neon. Production defines `DATABASE_URL` with `sslmode=require` and does not define `TEST_DATABASE_URL`.
- The existing Todo deployment behavior remains unchanged except that it only triggers for Todo files or its own workflow.
- User-specific credentials are never invented in implementation. Example environment files contain intentionally invalid example values and the server runbook requires replacing them before first deployment.
- Each task ends with its own verification and commit.

---

## File Map

**Modify**

- `frontend/lib/api.ts`: resolve production API requests to the current origin.
- `frontend/.env.production`: stop embedding the local backend address.
- `frontend/Dockerfile`: build and run an optimized production Next.js image.
- `backend/Dockerfile`: build a smaller non-root production FastAPI image.
- `backend/tests/chatbot/test_memory_repository.py`: remove the wall-clock-dependent test failure that blocks CI.
- `.github/workflows/main.yml`: scope the Todo workflow to Todo changes.
- `README.md`: link to the server deployment runbook.

**Create**

- `frontend/lib/api.test.ts`: API base URL behavior tests.
- `frontend/.dockerignore`: frontend build-context exclusions.
- `backend/.dockerignore`: backend build-context exclusions.
- `deploy/docker-compose.yml`: image-based production Compose definition.
- `deploy/.deploy.env.example`: immutable image coordinates and deployment tag interface.
- `deploy/backend.env.example`: production backend runtime configuration interface.
- `deploy/deploy.sh`: pull, health-check, and rollback implementation.
- `deploy/nginx/paiguangguang.conf`: IP/port reverse-proxy routes and SSE settings.
- `deploy/nginx/docker-compose.web.yml`: additive override joining the existing Nginx service to `web` and publishing port 8080.
- `deploy/README.md`: exact one-time server setup and operational commands.
- `.github/workflows/deploy-paiguangguang.yml`: validation, GHCR publish, SSH deployment, and concurrency control.

---

### Task 1: Make the frontend API base same-origin in production

**Files:**

- Create: `frontend/lib/api.test.ts`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/.env.production`

**Interfaces:**

- Produces: `getBackendBaseUrl(): string`, returning `""` when no public backend URL is configured and a trailing-slash-free absolute URL when configured.
- Consumed by: all existing JSON, form-data, and Chatbot SSE requests.

- [ ] **Step 1: Add failing API base tests**

```ts
import { afterEach, describe, expect, it, vi } from "vitest";

import { getBackendBaseUrl } from "@/lib/api";

describe("getBackendBaseUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("uses same-origin requests when no backend URL is configured", () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_URL", "");
    expect(getBackendBaseUrl()).toBe("");
  });

  it("normalizes a configured backend URL", () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_URL", " https://api.example.test/ ");
    expect(getBackendBaseUrl()).toBe("https://api.example.test");
  });
});
```

- [ ] **Step 2: Run the new tests and confirm the current localhost fallback fails**

Run from `frontend`:

```bash
npm test -- --run lib/api.test.ts
```

Expected: the same-origin test fails because the current function returns `http://127.0.0.1:8000`.

- [ ] **Step 3: Implement same-origin resolution**

Replace the current default and resolver in `frontend/lib/api.ts` with:

```ts
export function getBackendBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  return configuredUrl ? configuredUrl.replace(/\/+$/, "") : "";
}
```

Set `frontend/.env.production` to:

```env
NEXT_PUBLIC_BACKEND_URL=
NEXT_PUBLIC_CHATBOT_ENABLED=true
```

- [ ] **Step 4: Verify targeted and full frontend behavior**

Run from `frontend`:

```bash
npm test -- --run lib/api.test.ts
npm test
npm run lint
npm run build
```

Expected: 2 targeted tests pass; the full suite, Lint, type checks, and Next.js build exit successfully.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/api.ts frontend/lib/api.test.ts frontend/.env.production
git commit -m "fix(frontend): use same-origin production API"
```

---

### Task 2: Make the backend test gate deterministic

**Files:**

- Modify: `backend/tests/chatbot/test_memory_repository.py`

**Interfaces:**

- Consumes: `app.chatbot.repositories.memory_repository._utcnow`.
- Produces: a test that always evaluates expiration against `2026-07-13T12:00:00Z`, independent of the runner's current date.

- [ ] **Step 1: Reproduce the existing failure**

Run from the project directory:

```bash
python -m pytest backend/tests/chatbot/test_memory_repository.py::test_list_owned_filters_active_candidate_and_expiry -q
```

Expected on dates after 2026-07-14: FAIL because `active_future` is evaluated against the real wall clock.

- [ ] **Step 2: Freeze the repository clock in the test**

Add this import:

```python
from app.chatbot.repositories import memory_repository as memory_repository_module
```

Change the test signature and freeze `_utcnow` immediately after defining `now`:

```python
def test_list_owned_filters_active_candidate_and_expiry(tmp_path, monkeypatch) -> None:
    session_factory = _build_session_factory(tmp_path)
    conversation_repo = ConversationRepository(session_factory)
    repo = MemoryRepository(session_factory)

    with session_factory() as session:
        owner = _create_user(session, email="owner@example.com")
        session.commit()

    conversation_id = _create_conversation(conversation_repo, owner.id, "Thread")
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(memory_repository_module, "_utcnow", lambda: now)
```

Keep the remainder of the test unchanged.

- [ ] **Step 3: Verify the targeted and complete backend suite**

Run from the project directory with an isolated Chroma path:

```bash
CHROMA_PATH=.pytest-chroma python -m pytest backend/tests/chatbot/test_memory_repository.py -q
CHROMA_PATH=.pytest-chroma python -m pytest backend/tests -q
```

Expected: the repository test file passes; the complete suite has zero failures. Delete `.pytest-chroma` after the run.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/chatbot/test_memory_repository.py
git commit -m "test(chatbot): freeze memory expiry clock"
```

---

### Task 3: Build production frontend and backend images

**Files:**

- Create: `frontend/.dockerignore`
- Modify: `frontend/Dockerfile`
- Create: `backend/.dockerignore`
- Modify: `backend/Dockerfile`

**Interfaces:**

- Produces: frontend image listening on 3000 and backend image listening on 8000.
- Consumed by: GHCR publish job and `deploy/docker-compose.yml`.

- [ ] **Step 1: Add frontend build-context exclusions**

Create `frontend/.dockerignore`:

```dockerignore
.next
node_modules
out
coverage
*.log
.env*
!.env.production
tsconfig.tsbuildinfo
.git
.gitignore
Dockerfile*
```

- [ ] **Step 2: Replace the frontend Dockerfile with a production multi-stage image**

```dockerfile
FROM node:20-alpine AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM dependencies AS builder
WORKDIR /app
ARG NEXT_PUBLIC_BACKEND_URL=
ARG NEXT_PUBLIC_CHATBOT_ENABLED=true
ENV NEXT_PUBLIC_BACKEND_URL=${NEXT_PUBLIC_BACKEND_URL}
ENV NEXT_PUBLIC_CHATBOT_ENABLED=${NEXT_PUBLIC_CHATBOT_ENABLED}
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup -S nextjs && adduser -S nextjs -G nextjs
COPY --from=builder --chown=nextjs:nextjs /app/package.json ./package.json
COPY --from=builder --chown=nextjs:nextjs /app/node_modules ./node_modules
COPY --from=builder --chown=nextjs:nextjs /app/.next ./.next
COPY --from=builder --chown=nextjs:nextjs /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/next.config.mjs ./next.config.mjs
USER nextjs
EXPOSE 3000
CMD ["npm", "start"]
```

- [ ] **Step 3: Add backend build-context exclusions**

Create `backend/.dockerignore`:

```dockerignore
__pycache__
.pytest_cache
.venv
venv
tests
evals
chroma
*.pyc
*.pyo
*.pyd
*.log
*.env
.env*
auth-login-private-key.pem
*.md
.git
.gitignore
Dockerfile*
```

- [ ] **Step 4: Replace the backend Dockerfile with a non-root production image**

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --home-dir /app app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini

USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Build and inspect both images locally**

Run from the project directory:

```bash
docker build --build-arg NEXT_PUBLIC_BACKEND_URL= --build-arg NEXT_PUBLIC_CHATBOT_ENABLED=true -t paiguangguang-frontend:test frontend
docker build -t paiguangguang-backend:test backend
docker image inspect paiguangguang-frontend:test --format '{{.Config.User}} {{json .Config.Cmd}}'
docker image inspect paiguangguang-backend:test --format '{{.Config.User}} {{json .Config.Cmd}}'
```

Expected: both builds succeed; frontend reports user `nextjs`; backend reports user `app`; neither command is a development server.

- [ ] **Step 6: Confirm build contexts exclude local credentials and dependencies**

Run:

```bash
docker build --no-cache --progress=plain -t paiguangguang-frontend:test frontend
docker run --rm --entrypoint sh paiguangguang-backend:test -c 'test ! -e /app/prod.env && test ! -e /app/auth-login-private-key.pem && test ! -d /app/tests'
```

Expected: frontend build does not copy host `node_modules`; backend image check exits 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/Dockerfile frontend/.dockerignore backend/Dockerfile backend/.dockerignore
git commit -m "build: add production container images"
```

---

### Task 4: Define the server Compose topology and Nginx routing

**Files:**

- Create: `deploy/docker-compose.yml`
- Create: `deploy/.deploy.env.example`
- Create: `deploy/backend.env.example`
- Create: `deploy/nginx/paiguangguang.conf`
- Create: `deploy/nginx/docker-compose.web.yml`

**Interfaces:**

- Consumes: `FRONTEND_IMAGE`, `BACKEND_IMAGE`, and `IMAGE_TAG` from `.deploy.env`; backend runtime settings from `backend.env`; `auth-login-private-key.pem` as a Compose secret.
- Produces: network aliases `paiguangguang-frontend` and `paiguangguang-backend` on external network `web`.

- [ ] **Step 1: Create the immutable image environment interface**

Create `deploy/.deploy.env.example`:

```env
FRONTEND_IMAGE=ghcr.io/totorokingdom/paiguangguang-frontend
BACKEND_IMAGE=ghcr.io/totorokingdom/paiguangguang-backend
IMAGE_TAG=
```

- [ ] **Step 2: Create the backend runtime environment example**

Create `deploy/backend.env.example`:

```env
DATABASE_URL=postgresql+psycopg://neon_user:neon_password@ep-sample.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
JWT_SECRET_KEY=example-invalid-jwt-secret-replace-on-server
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
ADMIN_USER_EMAIL=admin@example.com
ADMIN_USER_PASSWORD=example-invalid-admin-password-replace-on-server
ADMIN_USER_DISPLAY_NAME=Admin
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=example-invalid-deepseek-key-replace-on-server
DEEPSEEK_CHAT_MODEL=deepseek-chat
DASHSCOPE_API_KEY=example-invalid-dashscope-key-replace-on-server
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHATBOT_ENV=production
CHATBOT_ENABLED=true
CHATBOT_DEFAULT_MODEL=deepseek-chat
CHATBOT_ALLOWED_MODELS=deepseek-chat
CHATBOT_LONG_TERM_MEMORY_ENABLED=false
CHATBOT_SEMANTIC_MEMORY_ENABLED=false
CORS_ALLOW_ORIGINS=http://1.12.47.29:8080
RAG_COLLECTION_NAME=portfolio_knowledge
```

Do not add `TEST_DATABASE_URL` to this file.

- [ ] **Step 3: Create the image-based production Compose file**

Create `deploy/docker-compose.yml`:

```yaml
name: paiguangguang

x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"

services:
  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - app_internal
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 10
    logging: *default-logging

  backend:
    image: "${BACKEND_IMAGE:?BACKEND_IMAGE is required}:${IMAGE_TAG:?IMAGE_TAG is required}"
    restart: unless-stopped
    env_file:
      - ./backend.env
    environment:
      REDIS_URL: redis://redis:6379/0
      CHROMA_PATH: /data/chroma
      AUTH_LOGIN_PRIVATE_KEY_PATH: /run/secrets/auth_login_private_key
    secrets:
      - auth_login_private_key
    volumes:
      - chroma_data:/data/chroma
    expose:
      - "8000"
    networks:
      web:
        aliases:
          - paiguangguang-backend
      app_internal: {}
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test:
        - CMD
        - python
        - -c
        - "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"
      interval: 15s
      timeout: 6s
      retries: 12
      start_period: 30s
    logging: *default-logging

  frontend:
    image: "${FRONTEND_IMAGE:?FRONTEND_IMAGE is required}:${IMAGE_TAG:?IMAGE_TAG is required}"
    restart: unless-stopped
    expose:
      - "3000"
    networks:
      web:
        aliases:
          - paiguangguang-frontend
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test:
        - CMD
        - node
        - -e
        - "fetch('http://127.0.0.1:3000/').then(r => { if (!r.ok) process.exit(1) }).catch(() => process.exit(1))"
      interval: 15s
      timeout: 6s
      retries: 12
      start_period: 20s
    logging: *default-logging

networks:
  web:
    external: true
    name: web
  app_internal:
    internal: true

volumes:
  redis_data:
  chroma_data:

secrets:
  auth_login_private_key:
    file: ./auth-login-private-key.pem
```

- [ ] **Step 4: Create the Nginx site configuration**

Create `deploy/nginx/paiguangguang.conf`:

```nginx
server {
    listen 80;
    server_name 1.12.47.29;

    client_max_body_size 12m;

    location /api/ {
        proxy_pass http://paiguangguang-backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        proxy_pass http://paiguangguang-frontend:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 5: Create an additive Compose override for the existing Nginx service**

Create `deploy/nginx/docker-compose.web.yml`:

```yaml
services:
  nginx:
    ports:
      - "8080:80"
    networks:
      - web

networks:
  web:
    external: true
    name: web
```

This assumes the existing service key is `nginx`. The server verification step must run `docker compose config --services` and confirm that exact service key before applying the override.

- [ ] **Step 6: Validate Compose and Nginx syntax locally**

Create temporary validation files from the examples, set `IMAGE_TAG` to 40 lowercase hexadecimal characters, and use an existing RSA test key only for syntax validation:

```bash
cp deploy/.deploy.env.example deploy/.deploy.env
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=0123456789abcdef0123456789abcdef01234567/' deploy/.deploy.env
cp deploy/backend.env.example deploy/backend.env
cp backend/auth-login-private-key.pem deploy/auth-login-private-key.pem
docker network inspect web >/dev/null 2>&1 || docker network create web
docker compose --env-file deploy/.deploy.env -f deploy/docker-compose.yml config --quiet
docker run --rm \
  --add-host paiguangguang-backend:127.0.0.1 \
  --add-host paiguangguang-frontend:127.0.0.1 \
  -v "$PWD/deploy/nginx/paiguangguang.conf:/etc/nginx/conf.d/paiguangguang.conf:ro" \
  nginx:alpine nginx -t
rm -f deploy/.deploy.env deploy/backend.env deploy/auth-login-private-key.pem
```

Expected: Compose and Nginx validation exit 0; no temporary credential or runtime environment file remains tracked.

- [ ] **Step 7: Commit**

```bash
git add deploy/docker-compose.yml deploy/.deploy.env.example deploy/backend.env.example deploy/nginx/paiguangguang.conf deploy/nginx/docker-compose.web.yml
git commit -m "ops: define production container topology"
```

---

### Task 5: Implement atomic deployment and image rollback

**Files:**

- Create: `deploy/deploy.sh`

**Interfaces:**

- Consumes: one required argument containing a 40-character lowercase Git SHA; `.deploy.env`; `docker-compose.yml`; an already authenticated Docker client.
- Produces: updated `IMAGE_TAG` after successful health checks, or restored previous tag after failure.

- [ ] **Step 1: Create the deployment script**

Create `deploy/deploy.sh`:

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/home/my-website-ui/paiguangguang"
DEPLOY_ENV="$APP_DIR/.deploy.env"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"
NEW_TAG="${1:-}"

if [[ ! "$NEW_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo "IMAGE_TAG must be a full lowercase Git commit SHA" >&2
  exit 2
fi

cd "$APP_DIR"
test -f "$DEPLOY_ENV"
test -f "$COMPOSE_FILE"
test -f "$APP_DIR/backend.env"
test -f "$APP_DIR/auth-login-private-key.pem"

previous_tag="$(sed -n 's/^IMAGE_TAG=//p' "$DEPLOY_ENV" | tail -n 1)"

write_tag() {
  local tag="$1"
  local temporary_file
  temporary_file="$(mktemp "$APP_DIR/.deploy.env.XXXXXX")"
  awk -v tag="$tag" '
    BEGIN { replaced = 0 }
    /^IMAGE_TAG=/ { print "IMAGE_TAG=" tag; replaced = 1; next }
    { print }
    END { if (!replaced) print "IMAGE_TAG=" tag }
  ' "$DEPLOY_ENV" > "$temporary_file"
  chmod 600 "$temporary_file"
  mv "$temporary_file" "$DEPLOY_ENV"
}

compose() {
  docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" "$@"
}

wait_for_public_routes() {
  local attempt
  for attempt in $(seq 1 36); do
    if curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/ >/dev/null \
      && curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/api/v1/health >/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

rollback() {
  if [[ "$previous_tag" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Deployment failed; restoring $previous_tag" >&2
    write_tag "$previous_tag"
    compose pull frontend backend
    compose up -d --remove-orphans --wait --wait-timeout 180
    wait_for_public_routes
  else
    echo "Deployment failed and no previous image tag is available" >&2
    write_tag ""
  fi
  if [[ "$previous_tag" =~ ^[0-9a-f]{40}$ ]]; then
    compose ps >&2 || true
  fi
  exit 1
}

write_tag "$NEW_TAG"

if ! compose pull frontend backend; then
  rollback
fi

if ! compose up -d --remove-orphans --wait --wait-timeout 180; then
  rollback
fi

if ! wait_for_public_routes; then
  rollback
fi

echo "Deployment succeeded: $NEW_TAG"
compose ps
```

- [ ] **Step 2: Validate the script before running it against Docker**

Run:

```bash
bash -n deploy/deploy.sh
bash deploy/deploy.sh invalid-tag
```

Expected: syntax check exits 0; invalid-tag exits 2 with the exact SHA validation message before touching Docker.

- [ ] **Step 3: Verify file permissions and shell safety**

Run:

```bash
chmod +x deploy/deploy.sh
git diff --check -- deploy/deploy.sh
```

Expected: no whitespace errors; Git records the executable bit.

- [ ] **Step 4: Commit**

```bash
git add deploy/deploy.sh
git commit -m "ops: add health-checked image rollback"
```

---

### Task 6: Add GitHub Actions validation, GHCR publishing, and SSH deployment

**Files:**

- Modify: `.github/workflows/main.yml`
- Create: `.github/workflows/deploy-paiguangguang.yml`

**Interfaces:**

- Consumes GitHub Secrets: `SERVER_HOST`, `SERVER_USER`, `SERVER_SSH_KEY`.
- Uses built-in `GITHUB_TOKEN` with `packages: write` for GHCR publishing.
- Produces two images tagged with `${{ github.sha }}` and invokes `/home/my-website-ui/paiguangguang/deploy.sh` with that SHA.

- [ ] **Step 1: Scope the existing Todo workflow**

Update its trigger without changing deployment steps:

```yaml
on:
  push:
    branches:
      - main
    paths:
      - "claude-code-todo-demo/**"
      - ".github/workflows/main.yml"
  workflow_dispatch:
```

- [ ] **Step 2: Create the Paiguangguang workflow**

Create `.github/workflows/deploy-paiguangguang.yml` at the Git repository root:

```yaml
name: Deploy Paiguangguang

on:
  push:
    branches:
      - main
    paths:
      - "paiguangguang/**"
      - ".github/workflows/deploy-paiguangguang.yml"
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: paiguangguang-production
  cancel-in-progress: false

env:
  FRONTEND_IMAGE: ghcr.io/totorokingdom/paiguangguang-frontend
  BACKEND_IMAGE: ghcr.io/totorokingdom/paiguangguang-backend

jobs:
  frontend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: paiguangguang/frontend
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: paiguangguang/frontend/package-lock.json
      - name: Install dependencies
        run: npm ci
      - name: Run tests
        run: npm test
      - name: Run lint
        run: npm run lint
      - name: Build frontend
        env:
          NEXT_PUBLIC_BACKEND_URL: ""
          NEXT_PUBLIC_CHATBOT_ENABLED: "true"
        run: npm run build

  backend-check:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: paiguangguang
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: paiguangguang/backend/requirements.txt
      - name: Install dependencies
        run: python -m pip install -r backend/requirements.txt
      - name: Run backend tests
        env:
          CHROMA_PATH: ${{ runner.temp }}/paiguangguang-chroma
        run: python -m pytest backend/tests -q

  publish-images:
    needs:
      - frontend-check
      - backend-check
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Build and push frontend
        uses: docker/build-push-action@v6
        with:
          context: ./paiguangguang/frontend
          file: ./paiguangguang/frontend/Dockerfile
          push: true
          build-args: |
            NEXT_PUBLIC_BACKEND_URL=
            NEXT_PUBLIC_CHATBOT_ENABLED=true
          tags: |
            ${{ env.FRONTEND_IMAGE }}:${{ github.sha }}
            ${{ env.FRONTEND_IMAGE }}:latest
          cache-from: type=gha,scope=paiguangguang-frontend
          cache-to: type=gha,mode=max,scope=paiguangguang-frontend
      - name: Build and push backend
        uses: docker/build-push-action@v6
        with:
          context: ./paiguangguang/backend
          file: ./paiguangguang/backend/Dockerfile
          push: true
          tags: |
            ${{ env.BACKEND_IMAGE }}:${{ github.sha }}
            ${{ env.BACKEND_IMAGE }}:latest
          cache-from: type=gha,scope=paiguangguang-backend
          cache-to: type=gha,mode=max,scope=paiguangguang-backend

  deploy:
    needs: publish-images
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
      - name: Upload deployment manifests
        uses: appleboy/scp-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          source: "paiguangguang/deploy/docker-compose.yml,paiguangguang/deploy/deploy.sh"
          target: "/tmp/paiguangguang-${{ github.sha }}"
          strip_components: 2
      - name: Deploy immutable images
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SERVER_SSH_KEY }}
          command_timeout: 15m
          script: |
            set -eu
            release_dir="/tmp/paiguangguang-${{ github.sha }}"
            app_dir="/home/my-website-ui/paiguangguang"
            install -d -m 755 "$app_dir"
            install -m 644 "$release_dir/docker-compose.yml" "$app_dir/docker-compose.yml"
            install -m 755 "$release_dir/deploy.sh" "$app_dir/deploy.sh"
            rm -rf "$release_dir"
            "$app_dir/deploy.sh" "${{ github.sha }}"
```

- [ ] **Step 3: Validate workflow structure**

Run from the Git root:

```bash
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest
```

Expected: actionlint exits 0 for both workflows. Confirm the Todo workflow still contains its original SCP and SSH deployment steps.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/main.yml .github/workflows/deploy-paiguangguang.yml
git commit -m "ci: publish and deploy GHCR images"
```

---

### Task 7: Write the server setup and operations runbook

**Files:**

- Create: `deploy/README.md`
- Modify: `README.md`

**Interfaces:**

- Consumes: the server's existing `/home/nginx/docker-compose.yml` and `nginx` service; Neon connection string; GitHub package read token; three existing GitHub SSH secrets.
- Produces: a reproducible one-time installation and recovery procedure.

- [ ] **Step 1: Write exact prerequisites and directory setup**

The runbook must require Docker Engine, Docker Compose v2, curl, outbound access to Neon and GHCR, and an existing Nginx service named `nginx`. Include these commands:

```bash
docker --version
docker compose version
curl --version
docker network inspect web >/dev/null 2>&1 || docker network create web
install -d -m 755 /home/my-website-ui/paiguangguang
```

Include this one-time upload command to run from the Git repository root on the maintainer workstation:

```bash
scp -r paiguangguang/deploy root@1.12.47.29:/home/my-website-ui/paiguangguang-bootstrap
scp paiguangguang/backend/auth-login-private-key.pem root@1.12.47.29:/home/my-website-ui/paiguangguang/auth-login-private-key.pem
```

- [ ] **Step 2: Document one-time Nginx integration**

Include:

```bash
cd /home/nginx
docker compose config --services
cp /home/my-website-ui/paiguangguang-bootstrap/nginx/paiguangguang.conf conf.d/paiguangguang.conf
docker compose -f docker-compose.yml -f /home/my-website-ui/paiguangguang-bootstrap/nginx/docker-compose.web.yml config --quiet
docker compose -f docker-compose.yml -f /home/my-website-ui/paiguangguang-bootstrap/nginx/docker-compose.web.yml up -d
docker compose exec nginx nginx -t
docker compose exec nginx nginx -s reload
```

State that the two-file Compose invocation must also be used for future Nginx recreations unless the override contents are merged into `/home/nginx/docker-compose.yml`.

- [ ] **Step 3: Document runtime file installation**

Include commands that copy examples without overwriting an existing runtime configuration:

```bash
cd /home/my-website-ui/paiguangguang
test -f .deploy.env || cp /home/my-website-ui/paiguangguang-bootstrap/.deploy.env.example .deploy.env
test -f backend.env || cp /home/my-website-ui/paiguangguang-bootstrap/backend.env.example backend.env
cp /home/my-website-ui/paiguangguang-bootstrap/docker-compose.yml docker-compose.yml
cp /home/my-website-ui/paiguangguang-bootstrap/deploy.sh deploy.sh
chmod 755 deploy.sh
chmod 600 .deploy.env backend.env auth-login-private-key.pem
```

Explicitly require:

- Replacing every `example-invalid-*` value.
- Replacing the sample Neon URL with the real `postgresql+psycopg` Neon URL ending in `sslmode=require`.
- Confirming `TEST_DATABASE_URL` is absent with `! grep -q '^TEST_DATABASE_URL=' backend.env`.
- Generating or copying the real RSA private key to `auth-login-private-key.pem`.

- [ ] **Step 4: Document GHCR login and GitHub repository settings**

Include:

```bash
echo "$GHCR_READ_TOKEN" | docker login ghcr.io -u TotoroKingdom --password-stdin
```

Require a package token with `read:packages` only, and list repository Secrets:

```text
SERVER_HOST=1.12.47.29
SERVER_USER=root
SERVER_SSH_KEY=the complete multiline private SSH key stored as a GitHub Actions secret
```

Recommend using a dedicated deployment account with Docker permission; if the existing root account is retained, restrict the SSH key to GitHub Actions and disable password login.

- [ ] **Step 5: Document verification, logs, backup, and rollback commands**

Include:

```bash
cd /home/my-website-ui/paiguangguang
docker compose --env-file .deploy.env -f docker-compose.yml ps
docker compose --env-file .deploy.env -f docker-compose.yml logs --tail=200 frontend backend redis
curl -fsS http://127.0.0.1:8080/
curl -fsS http://127.0.0.1:8080/api/v1/health
docker volume inspect paiguangguang_redis_data
docker volume inspect paiguangguang_chroma_data
```

Document that application rollback changes `IMAGE_TAG`; it does not reverse Neon schema migrations or data changes. Document backing up Redis AOF and Chroma volume data before destructive maintenance.

- [ ] **Step 6: Link the runbook from the project README**

Add a production deployment section linking `deploy/README.md` and the architecture design. Do not duplicate the full runbook in the root README.

- [ ] **Step 7: Verify documentation commands and commit**

Run:

```bash
rg -n "1\.12\.47\.29:8080|GHCR|Neon|TEST_DATABASE_URL|deploy\.sh|rollback" deploy/README.md README.md
git diff --check -- deploy/README.md README.md
```

Expected: every operational topic is present and no whitespace errors are reported.

Commit:

```bash
git add deploy/README.md README.md
git commit -m "docs: add production deployment runbook"
```

---

### Task 8: Run the complete release verification

**Files:**

- Verify only; fix failures in the task that owns the relevant file and amend that task's commit before continuing.

**Interfaces:**

- Produces: evidence that the code, images, Compose topology, Nginx routing, and Actions syntax are ready for the first server deployment.

- [ ] **Step 1: Verify the worktree contains only intended commits and files**

```bash
git status --short
git log --oneline -10
```

Expected: clean status and the commits from Tasks 1-7 are visible.

- [ ] **Step 2: Run complete frontend verification**

```bash
cd frontend
npm ci
npm test
npm run lint
npm run build
cd ..
```

Expected: all tests pass, Lint reports no errors, and production build exits 0.

- [ ] **Step 3: Run complete backend verification with isolated state**

```bash
CHROMA_PATH=.pytest-chroma python -m pytest backend/tests -q
rm -rf .pytest-chroma
```

Expected: zero failed tests and no tracked Chroma database changes.

- [ ] **Step 4: Build both production images**

```bash
docker build --build-arg NEXT_PUBLIC_BACKEND_URL= --build-arg NEXT_PUBLIC_CHATBOT_ENABLED=true -t paiguangguang-frontend:verify frontend
docker build -t paiguangguang-backend:verify backend
```

Expected: both images build successfully from clean contexts.

- [ ] **Step 5: Validate Compose, Nginx, shell, and Actions**

```bash
bash -n deploy/deploy.sh
cp deploy/.deploy.env.example deploy/.deploy.env
sed -i 's/^IMAGE_TAG=.*/IMAGE_TAG=0123456789abcdef0123456789abcdef01234567/' deploy/.deploy.env
cp deploy/backend.env.example deploy/backend.env
cp backend/auth-login-private-key.pem deploy/auth-login-private-key.pem
docker network inspect web >/dev/null 2>&1 || docker network create web
docker compose --env-file deploy/.deploy.env -f deploy/docker-compose.yml config --quiet
docker run --rm \
  --add-host paiguangguang-backend:127.0.0.1 \
  --add-host paiguangguang-frontend:127.0.0.1 \
  -v "$PWD/deploy/nginx/paiguangguang.conf:/etc/nginx/conf.d/paiguangguang.conf:ro" \
  nginx:alpine nginx -t
rm -f deploy/.deploy.env deploy/backend.env deploy/auth-login-private-key.pem
cd ..
docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest
cd paiguangguang
```

Expected: every command exits 0 and all temporary validation files are removed afterward.

- [ ] **Step 6: Perform first-server deployment and verify externally**

After the GitHub repository Secrets and server bootstrap are complete, manually trigger `Deploy Paiguangguang`, then run:

```bash
curl -fsS http://1.12.47.29:8080/ >/dev/null
curl -fsS http://1.12.47.29:8080/api/v1/health
```

Expected: frontend returns HTTP 200; health returns a successful API envelope. In browser DevTools, confirm login and Chatbot requests target `http://1.12.47.29:8080/api/...` and streaming responses arrive incrementally.

- [ ] **Step 7: Record the deployed immutable version**

On the server:

```bash
cd /home/my-website-ui/paiguangguang
grep '^IMAGE_TAG=' .deploy.env
docker compose --env-file .deploy.env -f docker-compose.yml images
```

Expected: `IMAGE_TAG` equals the GitHub Actions commit SHA and both application images use that exact tag.
