#!/bin/bash
# Sync Webshop: Production Deployment Script
# Usage: ./deploy.sh [backend|frontend|all]

TARGET_IP="194.163.131.237"
BACKEND_DIR="/home/frappe/frappe-bench/apps/sync_webshop"
FRONTEND_DIR="/var/www/sync_webshop"

deploy_backend() {
    echo "--- Deploying Backend ---"
    scp -r sync_webshop/ root@$TARGET_IP:$BACKEND_DIR/
    ssh root@$TARGET_IP "systemctl restart sync-webshop-api.service"
    echo "Backend deployed and service restarted."
}

deploy_frontend() {
    echo "--- Deploying Frontend ---"
    # Assuming the frontend is already built in the local dist folder
    if [ -d "../sync_webshop_frontend/dist" ]; then
        scp -r ../sync_webshop_frontend/dist/* root@$TARGET_IP:$FRONTEND_DIR/
        echo "Frontend assets synchronized."
    else
        echo "Error: Frontend dist directory not found. Please build the frontend first."
    fi
}

case "$1" in
    backend)
        deploy_backend
        ;;
    frontend)
        deploy_frontend
        ;;
    all|*)
        deploy_backend
        deploy_frontend
        ;;
esac

echo "Deployment cycle complete."
