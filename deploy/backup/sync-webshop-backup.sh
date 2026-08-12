#!/usr/bin/env bash
set -euo pipefail

BENCH_PATH="${BENCH_PATH:-/home/frappe/frappe-bench}"
SITE_NAME="${SITE_NAME:-erpnext.localhost}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

cd "$BENCH_PATH"
runuser -u frappe -- env PATH="$BENCH_PATH/env/bin:/home/frappe/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin" SITES_PATH="$BENCH_PATH/sites" bench --site "$SITE_NAME" backup --with-files
find "$BENCH_PATH/sites/$SITE_NAME/private/backups" -type f -mtime "+$RETENTION_DAYS" -delete
