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
