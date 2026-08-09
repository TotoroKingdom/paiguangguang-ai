# Production database environment deployment design

## Objective

Deploy the tracked `backend/prod.env` file with every production release and make the backend container use the PostgreSQL 17 container running on the same server.

## Configuration flow

- Local development continues to use `backend/dev.env`, including its SSL-required local tunnel URLs.
- Production uses `backend/prod.env`; `deploy/backend.env.example` is removed.
- GitHub Actions uploads `backend/prod.env` together with the deployment manifests.
- The release step installs it at `/home/my-website-ui/paiguangguang/backend/prod.env` with mode `600`.
- `deploy/docker-compose.yml` loads `./backend/prod.env` for the backend service.
- `deploy/deploy.sh` rejects a release when the production environment file is absent.

## Database connection

The production application role is `paiguangguang`, the database is `knowledge_rag_agent`, and the password contains an `@` character. The password is percent-encoded in the SQLAlchemy URL:

```env
DATABASE_URL=postgresql+psycopg://paiguangguang:postgres%40paiguangguang@postgres17:5432/knowledge_rag_agent
```

Production does not define `TEST_DATABASE_URL`, because the current database resolver gives that variable precedence over `DATABASE_URL`. The internal Docker connection does not request SSL because the existing PostgreSQL container has no PostgreSQL TLS configuration.

## Container networking

Running both containers on the same server is not sufficient: container-local `localhost` cannot reach another container. The application Compose file declares an external database network, attaches the backend to it, and the deployment script idempotently creates that network and connects the existing `postgres17` container before starting the application.

PostgreSQL remains bound to server loopback as currently configured. No public port or firewall change is required.

## Deployment and failure handling

- The workflow uploads the production environment file on every release, so repository configuration is authoritative.
- The SSH release step creates the destination directory and installs the file before invoking `deploy.sh`.
- The deployment script checks that `postgres17` exists and is running, prepares the shared network, validates the Compose configuration, and then follows the existing image-pull, startup, health-check, and rollback flow.
- Image rollback does not roll back `backend/prod.env`; the current repository version remains authoritative. Changes to this file therefore need to remain compatible with the previous application image used by rollback.

## Verification

- Configuration tests distinguish development and production database URLs and assert that production has no `TEST_DATABASE_URL`.
- Static checks verify that the workflow uploads and installs `backend/prod.env` and that no deployment file references `backend.env.example`.
- `docker compose config` verifies the resolved application and PostgreSQL Compose files.
- Backend tests verify that configuration and database URL resolution still behave as expected.
