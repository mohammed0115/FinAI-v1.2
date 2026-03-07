#!/bin/bash
# Startup script for FinAI Django application
# This script runs migrations and initializes the database before starting the server

set -e

echo "================================================"
echo "FinAI Django Application Startup"
echo "================================================"

cd /app/backend

# Wait for any file system to be ready
sleep 2

echo "[1/4] Running database migrations..."
python manage.py migrate --noinput

echo "[2/4] Collecting static files..."
python manage.py collectstatic --noinput --clear || echo "Static files collection skipped"

echo "[3/4] Initializing database with default data..."
python manage.py init_db || echo "Database already initialized"

echo "[4/4] Starting application server..."
echo "================================================"
echo "Server starting on 0.0.0.0:8001"
echo "Health check: http://localhost:8001/health"
echo "================================================"

# Start the server with uvicorn
exec python -m uvicorn server:app --host 0.0.0.0 --port 8001 --workers 1
