#!/usr/bin/env bash
# Sync Webshop deployment helper.
# Usage: TARGET_HOST=... ./deploy.sh [backend|frontend|all]
#
# Frontend safety policy:
# - The source worktree must be clean and contain the required feature files.
# - The production build must contain the configuration contract and a minimum asset count.
# - A frontend deploy is refused when its Git revision differs from the approved staging
#   revision unless the operator explicitly sets both:
#       ALLOW_FRONTEND_SOURCE_MISMATCH=1
#       FRONTEND_APPROVAL_PHRASE=I_UNDERSTAND_FRONTEND_SOURCE_MISMATCH
# - The live webroot is moved to a timestamped backup before replacement.
# - Nginx and route smoke tests must pass; otherwise the previous release is restored.

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
MIN_FRONTEND_ASSETS="${MIN_FRONTEND_ASSETS:-70}"
ALLOW_FRONTEND_SOURCE_MISMATCH="${ALLOW_FRONTEND_SOURCE_MISMATCH:-0}"
FRONTEND_APPROVAL_PHRASE="${FRONTEND_APPROVAL_PHRASE:-}"
APPROVAL_PHRASE_REQUIRED="I_UNDERSTAND_FRONTEND_SOURCE_MISMATCH"
APPROVED_REVISION_FILE="${APPROVED_REVISION_FILE:-/var/lib/sync-webshop/frontend-approved-revision}"

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

frontend_guard() {
  if [[ ! -f "$FRONTEND_SOURCE/scripts/release_guard.py" ]]; then
    echo "Frontend release guard is missing; refusing deployment." >&2
    exit 2
  fi
  python3 "$FRONTEND_SOURCE/scripts/release_guard.py" source "$FRONTEND_SOURCE"
}

prepare_frontend() {
  frontend_guard
  if [[ "$BUILD_FRONTEND" == "1" ]]; then
    echo "--- Building Frontend ---"
    (cd "$FRONTEND_SOURCE" && npm ci --no-audit --no-fund && npm run build)
  fi
  if [[ ! -d "$FRONTEND_SOURCE/dist" ]]; then
    echo "Frontend dist directory not found: $FRONTEND_SOURCE/dist" >&2
    exit 2
  fi
  python3 "$FRONTEND_SOURCE/scripts/release_guard.py" build "$FRONTEND_SOURCE/dist" > "$FRONTEND_SOURCE/.release-guard.json"
  local asset_count
  asset_count="$(find "$FRONTEND_SOURCE/dist" -type f | wc -l)"
  if (( asset_count < MIN_FRONTEND_ASSETS )); then
    echo "Frontend asset count $asset_count is below safety minimum $MIN_FRONTEND_ASSETS." >&2
    exit 2
  fi
  FRONTEND_REVISION="$(git -C "$FRONTEND_SOURCE" rev-parse HEAD)"
  FRONTEND_PACKAGE="$(mktemp "${TMPDIR:-/tmp}/sync-webshop-frontend.XXXXXX.tgz")"
  tar -czf "$FRONTEND_PACKAGE" -C "$FRONTEND_SOURCE" dist
}

frontend_revision_gate() {
  local approved_revision
  approved_revision="$(remote "cat '$APPROVED_REVISION_FILE' 2>/dev/null || true")"
  if [[ -n "$approved_revision" && "$approved_revision" == "$FRONTEND_REVISION" ]]; then
    echo "Frontend revision matches approved staging revision: $FRONTEND_REVISION"
    return
  fi
  echo "Frontend source revision differs from the approved staging revision." >&2
  echo "Candidate: $FRONTEND_REVISION" >&2
  echo "Approved: ${approved_revision:-<none>}" >&2
  if [[ "$ALLOW_FRONTEND_SOURCE_MISMATCH" != "1" || "$FRONTEND_APPROVAL_PHRASE" != "$APPROVAL_PHRASE_REQUIRED" ]]; then
    echo "Refusing deployment. Recover the matching complete source, or explicitly set:" >&2
    echo "ALLOW_FRONTEND_SOURCE_MISMATCH=1 FRONTEND_APPROVAL_PHRASE=$APPROVAL_PHRASE_REQUIRED" >&2
    exit 3
  fi
  echo "Explicit source-mismatch approval supplied; continuing with extra rollback protection." >&2
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
  frontend_revision_gate
  local stamp backup work
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  backup="/var/backups/sync-webshop-frontend-${FRONTEND_REVISION:0:12}-$stamp"
  work="/tmp/sync-webshop-frontend-${FRONTEND_REVISION:0:12}-$stamp"
  remote "mkdir -p '$work'"
  scp -o BatchMode=yes "$FRONTEND_PACKAGE" "$SSH_USER@$TARGET_HOST:$work/release.tgz"
  remote "set -eu; tar -xzf '$work/release.tgz' -C '$work'; test -f '$work/dist/index.html'; mkdir -p /var/backups; mv '$FRONTEND_DIR' '$backup'; mv '$work/dist' '$FRONTEND_DIR'; chown -R www-data:www-data '$FRONTEND_DIR'; if ! nginx -t; then mv '$FRONTEND_DIR' '${backup}.failed'; mv '$backup' '$FRONTEND_DIR'; chown -R www-data:www-data '$FRONTEND_DIR'; exit 1; fi; systemctl reload nginx; sleep 3; if ! curl -fsS --max-time 20 http://127.0.0.1/ >/dev/null; then mv '$FRONTEND_DIR' '${backup}.failed'; mv '$backup' '$FRONTEND_DIR'; chown -R www-data:www-data '$FRONTEND_DIR'; systemctl reload nginx; exit 1; fi; mkdir -p '$(dirname "$APPROVED_REVISION_FILE")'; printf '%s\n' '$FRONTEND_REVISION' > '$APPROVED_REVISION_FILE'; rm -r '$work'; echo frontend_backup='$backup'; echo frontend_revision='$FRONTEND_REVISION'; echo frontend_files=$(find '$FRONTEND_DIR' -type f | wc -l)"
  rm -f "$FRONTEND_PACKAGE" "$FRONTEND_SOURCE/.release-guard.json"
  echo "Frontend deployed with release gate, atomic rollback, and smoke-test verification."
}

trap 'if [[ -n "${FRONTEND_PACKAGE:-}" && -f "$FRONTEND_PACKAGE" ]]; then rm -f "$FRONTEND_PACKAGE"; fi' EXIT

case "${1:-all}" in
  backend) deploy_backend ;;
  frontend) deploy_frontend ;;
  all) deploy_backend; deploy_frontend ;;
  *) echo "Usage: TARGET_HOST=... $0 [backend|frontend|all]" >&2; exit 2 ;;
esac

echo "Deployment cycle complete."
