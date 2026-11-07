# Deployment Notes

## Runtime

`frontend` is the only published container and binds `127.0.0.1:3000`. `backend` is reachable only on the Compose network. The frontend server rewrites `/api/v1/*` to `http://backend:8000/api/v1/*` at image build time. SQLite is mounted at `/data/assistant.db` through the named volume `paiguangguang-ai-assistant-data`.

Production must provide a stable `ASSISTANT_OWNER_COOKIE_SECRET` with at least 32 characters, `ASSISTANT_OWNER_COOKIE_SECURE=true`, and the public site origin in `ASSISTANT_ALLOWED_ORIGINS`. The backend exits before serving if the secret or secure-cookie requirement is not satisfied.

## Migrations and backup

The backend entrypoint runs `python -m alembic upgrade head` before Uvicorn. For an existing database, stop the backend or take a consistent SQLite backup first, for example with SQLite's backup API or `sqlite3 /data/assistant.db ".backup '/backup/assistant-$(date +%Y%m%d-%H%M%S).db'"`, then deploy. Keep the backup outside the Docker volume until the migration and health check succeed.

`docker compose up -d` and `docker compose up -d --remove-orphans` preserve the named volume. Do not use `docker compose down -v` in production. A rollback restores the previous image tags and, if a migration is not backward compatible, restores the pre-migration backup before starting the old image.

