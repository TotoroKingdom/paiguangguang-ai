#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/home/my-website-ui/paiguangguang"
DEPLOY_ENV="$APP_DIR/.deploy.env"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"
NEW_TAG="${1:-}"
NEW_FRONTEND_IMAGE="${2:-}"
NEW_BACKEND_IMAGE="${3:-}"

if [[ ! "$NEW_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo "IMAGE_TAG must be a full lowercase Git commit SHA" >&2
  exit 2
fi

validate_image_base() {
  local image="$1"
  [[ "$image" == */*/* ]] \
    && [[ ! "$image" =~ [[:space:]] ]] \
    && [[ "$image" != *@* ]] \
    && [[ "${image##*/}" != *:* ]]
}

if ! validate_image_base "$NEW_FRONTEND_IMAGE"; then
  echo "FRONTEND_IMAGE must be an untagged registry/namespace/repository path" >&2
  exit 2
fi

if ! validate_image_base "$NEW_BACKEND_IMAGE"; then
  echo "BACKEND_IMAGE must be an untagged registry/namespace/repository path" >&2
  exit 2
fi

cd "$APP_DIR"
test -f "$DEPLOY_ENV"
test -f "$COMPOSE_FILE"
test -f "$APP_DIR/backend.env"
test -f "$APP_DIR/auth-login-private-key.pem"
test -f /home/my-website-ui/todo-demo-ui/todo-app.html

read_deploy_value() {
  local key="$1"
  sed -n "s/^${key}=//p" "$DEPLOY_ENV" | tail -n 1
}

previous_frontend_image="$(read_deploy_value FRONTEND_IMAGE)"
previous_backend_image="$(read_deploy_value BACKEND_IMAGE)"
previous_tag="$(read_deploy_value IMAGE_TAG)"

write_deploy_state() {
  local frontend_image="$1"
  local backend_image="$2"
  local tag="$3"
  local temporary_file
  temporary_file="$(mktemp "$APP_DIR/.deploy.env.XXXXXX")"
  awk \
    -v frontend_image="$frontend_image" \
    -v backend_image="$backend_image" \
    -v tag="$tag" '
    BEGIN { frontend_replaced = 0; backend_replaced = 0; tag_replaced = 0 }
    /^FRONTEND_IMAGE=/ { print "FRONTEND_IMAGE=" frontend_image; frontend_replaced = 1; next }
    /^BACKEND_IMAGE=/ { print "BACKEND_IMAGE=" backend_image; backend_replaced = 1; next }
    /^IMAGE_TAG=/ { print "IMAGE_TAG=" tag; tag_replaced = 1; next }
    { print }
    END {
      if (!frontend_replaced) print "FRONTEND_IMAGE=" frontend_image
      if (!backend_replaced) print "BACKEND_IMAGE=" backend_image
      if (!tag_replaced) print "IMAGE_TAG=" tag
    }
  ' "$DEPLOY_ENV" > "$temporary_file"
  chmod 600 "$temporary_file"
  mv "$temporary_file" "$DEPLOY_ENV"
}

compose() {
  docker compose --env-file "$DEPLOY_ENV" -f "$COMPOSE_FILE" "$@"
}

pull_images() {
  local attempt
  for attempt in 1 2 3; do
    if compose pull frontend backend; then
      return 0
    fi
    if [[ "$attempt" -lt 3 ]]; then
      echo "Image pull attempt $attempt failed; retrying" >&2
      sleep $((attempt * 10))
    fi
  done
  return 1
}

wait_for_public_routes() {
  local attempt
  for attempt in $(seq 1 36); do
    if curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/ >/dev/null \
      && curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8080/api/v1/health >/dev/null \
      && curl --fail --silent --show-error --max-time 10 http://127.0.0.1:8082/ >/dev/null; then
      return 0
    fi
    sleep 5
  done
  return 1
}

rollback() {
  if [[ "$previous_tag" =~ ^[0-9a-f]{40}$ ]] \
    && validate_image_base "$previous_frontend_image" \
    && validate_image_base "$previous_backend_image"; then
    echo "Deployment failed; restoring $previous_tag" >&2
    write_deploy_state "$previous_frontend_image" "$previous_backend_image" "$previous_tag"
    compose up -d --remove-orphans --wait --wait-timeout 180
    wait_for_public_routes
  else
    echo "Deployment failed and no previous image tag is available" >&2
    write_deploy_state "$previous_frontend_image" "$previous_backend_image" "$previous_tag"
  fi
  if [[ "$previous_tag" =~ ^[0-9a-f]{40}$ ]]; then
    compose ps >&2 || true
  fi
  exit 1
}

write_deploy_state "$NEW_FRONTEND_IMAGE" "$NEW_BACKEND_IMAGE" "$NEW_TAG"

if ! pull_images; then
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
