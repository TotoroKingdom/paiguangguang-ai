# Deployment Notes

## Runtime

`frontend` is the only published container and binds `127.0.0.1:3000`. `backend` is reachable only on the Compose network. The frontend server rewrites `/api/v1/*` to `http://backend:8000/api/v1/*` at image build time. SQLite is mounted at `/data/assistant.db` through the named volume `paiguangguang-ai-assistant-data`.

Production must provide a stable `ASSISTANT_OWNER_COOKIE_SECRET` with at least 32 characters, `ASSISTANT_OWNER_COOKIE_SECURE=true`, and the public site origin in `ASSISTANT_ALLOWED_ORIGINS`. The backend exits before serving if the secret or secure-cookie requirement is not satisfied.

The GitHub Actions production job first runs the reusable application CI. Only a successful CI run can build the two SHA-tagged images and deploy `main`. A push to `dev` runs CI but never triggers production deployment.

The deployment workflow accepts a legacy `.env` that contains only `IMAGE_NAME=...`. It preserves the previous running frontend image ID, writes a fresh mode-`600` configuration, reuses `ASSISTANT_DATA_VOLUME` when present (otherwise the default named volume), and restores the previous Compose file, environment, and image if the release fails before the health checks complete. Never commit or print the production cookie secret.

## Migrations and backup

The backend entrypoint runs `python -m alembic upgrade head` before Uvicorn. For an existing database, stop the backend or take a consistent SQLite backup first, for example with SQLite's backup API or `sqlite3 /data/assistant.db ".backup '/backup/assistant-$(date +%Y%m%d-%H%M%S).db'"`, then deploy. Keep the backup outside the Docker volume until the migration and health check succeed.

`docker compose up -d` and `docker compose up -d --remove-orphans` preserve the named volume. Do not use `docker compose down -v` in production. A rollback restores the previous image tags and, if a migration is not backward compatible, restores the pre-migration backup before starting the old image.

The workflow creates the consistent SQLite backup automatically before starting the new backend. A backup failure aborts the release. Successful deployments write `/opt/paiguangguang-ai/.deployment-record` with the commit SHA, immutable image tags, data volume name, and UTC deployment time.

## Production verification

The workflow checks both container health and the public `https://.../api/v1/health` endpoint. A failed public check triggers the saved Compose/environment rollback. Treat GitHub Actions success as delivery evidence only: after the job completes, verify assistant session creation, message persistence after refresh, and persistence after a container restart. Record the deployed commit and image SHA with the observed test result. If server access, production variables/secrets, HTTPS, or a restorable backup is unavailable, stop before deployment and report the release as blocked.

