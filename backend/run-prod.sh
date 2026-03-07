#!/bin/bash

# ============================================================================
# FinAI Production Startup Script
# Optimized for production deployments with systemd/supervisor integration
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR${NC} $1" | tee -a "$LOG_FILE"
}

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/production.log"
PID_FILE="$LOG_DIR/finai.pid"
VENV_PATH="$SCRIPT_DIR/venv"
PORT=${PORT:-8000}
WORKERS=${WORKERS:-4}
TIMEOUT=${TIMEOUT:-30}

# Create log directory
mkdir -p "$LOG_DIR"

# ============================================================================
# CHECKS
# ============================================================================

print_info "Starting FinAI Production Server..."
print_info "Script directory: $SCRIPT_DIR"
print_info "Log file: $LOG_FILE"

# Check .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    print_error ".env not found at $SCRIPT_DIR/.env"
    exit 1
fi

print_info "Loading environment from .env"
set -a
source "$SCRIPT_DIR/.env" 2>/dev/null || true
set +a

# Check venv
if [ ! -d "$VENV_PATH" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    print_success "Virtual environment created"
fi

# Activate venv
source "$VENV_PATH/bin/activate"
print_success "Virtual environment activated"

# ============================================================================
# SETUP
# ============================================================================

print_info "Installing/updating dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null 2>&1
pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
pip install gunicorn > /dev/null 2>&1  # Ensure Gunicorn is installed
print_success "Dependencies ready"

# Run migrations
print_info "Running database migrations..."
cd "$SCRIPT_DIR"
python manage.py migrate --noinput

# Collect static files
print_info "Collecting static files..."
python manage.py collectstatic --noinput > /dev/null

# Compile translations
print_info "Compiling translations..."
python manage.py compilemessages > /dev/null 2>&1 || true

print_success "Application setup complete"

# ============================================================================
# START SERVER
# ============================================================================

print_info "Starting Gunicorn server..."
print_info "  Bind: 0.0.0.0:$PORT"
print_info "  Workers: $WORKERS"
print_info "  Timeout: $TIMEOUT seconds"
print_info "  Process ID will be saved to: $PID_FILE"

# Start Gunicorn
gunicorn \
    FinAI.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers $WORKERS \
    --worker-class sync \
    --timeout $TIMEOUT \
    --pidfile "$PID_FILE" \
    --access-logfile "$LOG_DIR/access.log" \
    --error-logfile "$LOG_DIR/error.log" \
    --log-level info \
    --graceful-timeout 30 \
    --keep-alive 5 \
    2>&1 | tee -a "$LOG_FILE"
