#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR="${1:-}"
NGINX_DIR="/home/nginx"
OVERRIDE_COMPOSE="$NGINX_DIR/docker-compose.web.yml"
STAMP="$(date +%F-%H%M%S)"
BACKUP_DIR="$NGINX_DIR/backups/$STAMP"

if [[ -z "$SOURCE_DIR" ]]; then
  echo "Usage: $0 /path/to/release/nginx" >&2
  exit 2
fi

for required_file in \
  "$SOURCE_DIR/paiguangguang.conf" \
  "$SOURCE_DIR/docker-compose.web.yml" \
  "$SOURCE_DIR/locations/draw.conf" \
  "$SOURCE_DIR/locations/todo.conf" \
  "$NGINX_DIR/nginx.conf" \
  "/home/my-website-ui/todo-demo-ui/todo-app.html" \
  "$NGINX_DIR/certs/www.paiguangguang.xyz.pem" \
  "$NGINX_DIR/certs/www.paiguangguang.xyz.key"; do
  test -f "$required_file"
done

install -d -m 755 "$BACKUP_DIR/conf.d/locations"

backup_file() {
  local relative_path="$1"
  local current_file="$NGINX_DIR/$relative_path"
  local backup_file="$BACKUP_DIR/$relative_path"

  install -d -m 755 "$(dirname "$backup_file")"
  if [[ -f "$current_file" ]]; then
    cp -a "$current_file" "$backup_file"
  else
    : > "$BACKUP_DIR/.missing-${relative_path//\//_}"
  fi
}

restore_file() {
  local relative_path="$1"
  local current_file="$NGINX_DIR/$relative_path"
  local backup_file="$BACKUP_DIR/$relative_path"
  local missing_marker="$BACKUP_DIR/.missing-${relative_path//\//_}"

  if [[ -f "$backup_file" ]]; then
    install -D -m 644 "$backup_file" "$current_file"
  elif [[ -f "$missing_marker" ]]; then
    rm -f -- "$current_file"
  fi
}

for relative_path in \
  conf.d/paiguangguang.conf \
  conf.d/locations/draw.conf \
  conf.d/locations/todo.conf; do
  backup_file "$relative_path"
done

install -d -m 755 "$NGINX_DIR/conf.d/locations"
install -m 644 "$SOURCE_DIR/docker-compose.web.yml" "$OVERRIDE_COMPOSE"
install -m 644 "$SOURCE_DIR/paiguangguang.conf" "$NGINX_DIR/conf.d/paiguangguang.conf"
install -m 644 "$SOURCE_DIR/locations/draw.conf" "$NGINX_DIR/conf.d/locations/draw.conf"
install -m 644 "$SOURCE_DIR/locations/todo.conf" "$NGINX_DIR/conf.d/locations/todo.conf"

compose() {
  docker compose -f "$OVERRIDE_COMPOSE" "$@"
}

restore_previous_configuration() {
  trap - ERR
  echo "Nginx deployment failed; restoring files from $BACKUP_DIR" >&2
  for relative_path in \
    conf.d/paiguangguang.conf \
    conf.d/locations/draw.conf \
    conf.d/locations/todo.conf; do
    restore_file "$relative_path"
  done

  if compose config --quiet; then
    compose up -d --force-recreate --wait --wait-timeout 60 nginx || true
    if compose exec -T nginx nginx -t; then
      compose exec -T nginx nginx -s reload || true
    fi
  fi
}

trap restore_previous_configuration ERR

compose config --quiet
compose up -d --force-recreate --wait --wait-timeout 60 nginx
compose exec -T nginx nginx -V 2>&1 \
  | grep -q -- '--with-http_sub_module'
compose exec -T nginx nginx -t

curl --fail --silent --show-error --max-time 20 \
  http://127.0.0.1:8081/ >/dev/null
curl --fail --silent --show-error --max-time 20 \
  http://127.0.0.1:8080/ >/dev/null
curl --fail --silent --show-error --max-time 20 \
  http://127.0.0.1:8080/api/v1/health >/dev/null
curl --fail --silent --show-error --max-time 20 \
  http://127.0.0.1:8082/ >/dev/null

curl --fail --silent --show-error --max-time 20 \
  --resolve www.paiguangguang.xyz:443:127.0.0.1 \
  https://www.paiguangguang.xyz/draw/ >/dev/null
curl --fail --silent --show-error --max-time 20 \
  --resolve www.paiguangguang.xyz:443:127.0.0.1 \
  https://www.paiguangguang.xyz/todo/ >/dev/null

trap - ERR

echo "Nginx deployment succeeded; backup: $BACKUP_DIR"
compose ps nginx
