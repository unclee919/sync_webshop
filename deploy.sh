#!/usr/bin/env bash
# Sync Webshop deployment helper.
# Usage: TARGET_HOST=... ./deploy.sh [backend|frontend|all]
# Optional: SSH_USER, BACKEND_DIR, FRONTEND_DIR, SERVICE_NAME, BUILD_FRONTEND.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_SOURCE="$SCRIPT_DIR"
FRONTEND_SOURCE="${FRONTEND_SOURCE:-$(cd "$SCRIPT_DIR/../sync_webshop_frontend" 2>/dev/null && pwd || true)}"
TARGET_HOST="${TARGET_HOST:-}"
SSH_USER="${SSH_USER:-root}"
BACKEND_DIR="${BACKEND_DIR:-/home/frappe/frappe-bench/apps/sync_webshop}"
FRONTEND_DIR="${FRONTEND_DIR:-/var/www/sync_webshop}"
SERVICE_NAME="${SERVICE_NAME:-sync-webshop-api.service}"
BUILD_FRONTEND="${BUILD_FRONTEND:-1}"

if [[ -z "$TARGET_HOST" ]]; then
  echo "TARGET_HOST is required; refusing to deploy to an implicit server." >&2
  exit 2
fi
if [[ ! -d "$BACKEND_SOURCE" ]]; then
  echo "Backend source directory not found: $BACKEND_SOURCE" >&2
  exit 2
fi
if [[ ! -d "$FRONTEND_SOURCE" ]]; then
  echo "Frontend source directory not found: $FRONTEND_SOURCE" >&2
  exit 2
fi

remote() {
  ssh -o BatchMode=yes "$SSH_USER@$TARGET_HOST" "$@"
}

prepare_frontend() {
  if [[ "$BUILD_FRONTEND" == "1" ]]; then
    echo "--- Building Frontend ---"
    (cd "$FRONTEND_SOURCE" && npm ci --no-audit --no-fund && npm run build)
  fi
  if [[ ! -d "$FRONTEND_SOURCE/dist" ]]; then
    echo "Frontend dist directory not found: $FRONTEND_SOURCE/dist" >&2
    exit 2
  fi
}

deploy_backend() {
  echo "--- Deploying Backend to $TARGET_HOST ---"
  remote "install -d -o $SSH_USER -g $SSH_USER '$BACKEND_DIR'"
  scp -o BatchMode=yes -r "$BACKEND_SOURCE"/. "$SSH_USER@$TARGET_HOST:$BACKEND_DIR/"
  remote "systemctl restart '$SERVICE_NAME' && systemctl is-active --quiet '$SERVICE_NAME'"
  remote "curl -fsS --max-time 20 http://127.0.0.1:8001/api/method/sync_webshop.api.content.get_content >/dev/null"
  echo "Backend deployed and health check passed."
}

deploy_frontend() {
  prepare_frontend
  echo "--- Deploying Frontend to $TARGET_HOST ---"
  remote "install -d '$FRONTEND_DIR'"
  scp -o BatchMode=yes -r "$FRONTEND_SOURCE"/dist/. "$SSH_USER@$TARGET_HOST:$FRONTEND_DIR/"
  remote "nginx -t && systemctl reload nginx"
  echo "Frontend assets deployed and nginx reloaded."
}

case "${1:-all}" in
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all) deploy_backend; deploy_frontend ;;
  *) echo "Usage: TARGET_HOST=... $0 [backend|frontend|all]" >&2; exit 2 ;;
esac

echo "Deployment cycle complete."
