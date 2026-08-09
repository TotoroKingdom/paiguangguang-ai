#!/usr/bin/env bash
set -Eeuo pipefail

CURRENT_TAG="${1:-}"
CURRENT_FRONTEND_IMAGE="${2:-}"
CURRENT_BACKEND_IMAGE="${3:-}"
PREVIOUS_TAG="${4:-}"
PREVIOUS_FRONTEND_IMAGE="${5:-}"
PREVIOUS_BACKEND_IMAGE="${6:-}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

validate_image_base() {
  local image="$1"
  [[ "$image" == */*/* ]] \
    && [[ ! "$image" =~ [[:space:]] ]] \
    && [[ "$image" != *@* ]] \
    && [[ "${image##*/}" != *:* ]]
}

if [[ ! "$CURRENT_TAG" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Current image tag must be a full lowercase Git commit SHA" >&2
  exit 2
fi

if ! validate_image_base "$CURRENT_FRONTEND_IMAGE" \
  || ! validate_image_base "$CURRENT_BACKEND_IMAGE"; then
  echo "Current frontend and backend image bases are invalid" >&2
  exit 2
fi

keep_previous=false
if [[ "$PREVIOUS_TAG" =~ ^[0-9a-f]{40}$ ]] \
  && validate_image_base "$PREVIOUS_FRONTEND_IMAGE" \
  && validate_image_base "$PREVIOUS_BACKEND_IMAGE"; then
  keep_previous=true
fi

is_target_repository() {
  case "${1##*/}" in
    paiguangguang-frontend | paiguangguang-backend) return 0 ;;
    *) return 1 ;;
  esac
}

is_kept_reference() {
  local reference="$1"
  [[ "$reference" == "$CURRENT_FRONTEND_IMAGE:$CURRENT_TAG" ]] \
    || [[ "$reference" == "$CURRENT_BACKEND_IMAGE:$CURRENT_TAG" ]] \
    || { [[ "$keep_previous" == true ]] \
      && { [[ "$reference" == "$PREVIOUS_FRONTEND_IMAGE:$PREVIOUS_TAG" ]] \
        || [[ "$reference" == "$PREVIOUS_BACKEND_IMAGE:$PREVIOUS_TAG" ]]; }; }
}

mapfile -t local_images < <("$DOCKER_BIN" image ls --format '{{.Repository}}|{{.Tag}}')

removed=0
failed=0
for image in "${local_images[@]}"; do
  IFS='|' read -r repository tag <<<"$image"
  if [[ -z "$repository" || "$tag" == "<none>" ]] \
    || ! is_target_repository "$repository"; then
    continue
  fi

  reference="$repository:$tag"
  if is_kept_reference "$reference"; then
    echo "Keeping application image $reference"
    continue
  fi

  echo "Removing old application image $reference"
  if "$DOCKER_BIN" image rm "$reference"; then
    removed=$((removed + 1))
  else
    echo "Warning: failed to remove $reference" >&2
    failed=$((failed + 1))
  fi
done

echo "Application image cleanup finished: removed=$removed failed=$failed"

