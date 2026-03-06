#!/bin/bash

# ============================================================================
# FinAI Application Runner Script
# Handles setup, migrations, and server startup
# ============================================================================

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${GREEN}===================================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===================================================${NC}"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# ============================================================================
# CONFIGURATION
# ============================================================================

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$SCRIPT_DIR"

# Default mode is 'dev'
MODE=${1:-dev}
PORT=${2:-8000}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

print_header "FinAI Application Startup"

# Check if .env exists
if [ ! -f "$BACKEND_DIR/.env" ]; then
    print_error ".env file not found at $BACKEND_DIR/.env"
    echo "Please create .env file first. You can copy from .env.example or run: ./run.sh setup"
    exit 1
fi

# Load environment variables
print_info "Loading environment variables from .env"
export $(cat "$BACKEND_DIR/.env" | grep -v '^#' | xargs)

# Check Python
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
print_success "Python $PYTHON_VERSION found"

# Check virtual environment
print_info "Checking virtual environment..."
if [ ! -d "$BACKEND_DIR/venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$BACKEND_DIR/venv"
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source "$BACKEND_DIR/venv/bin/activate"
print_success "Virtual environment activated"

# Install/upgrade dependencies
print_info "Installing/upgrading dependencies..."
pip install --upgrade pip setuptools wheel > /dev/null
pip install -r "$BACKEND_DIR/requirements.txt" > /dev/null
print_success "Dependencies installed"

# ============================================================================
# DATABASE MIGRATIONS
# ============================================================================

print_header "Database Setup"

print_info "Running database migrations..."
cd "$BACKEND_DIR"

# Makemigrations for main apps
print_info "Creating migrations..."
python manage.py makemigrations core analytics documents compliance ai_plugins --noinput > /dev/null 2>&1 || true
print_success "Migration files created/updated"

# Run migrations
print_info "Applying migrations..."
python manage.py migrate --noinput

print_success "Database migrations completed"

# ============================================================================
# COLLECTSTATIC
# ============================================================================

if [ "$MODE" == "prod" ]; then
    print_header "Collecting Static Files"
    print_info "Collecting static files..."
    python manage.py collectstatic --noinput > /dev/null
    print_success "Static files collected"
fi

# ============================================================================
# START SERVER
# ============================================================================

print_header "Starting Application"

if [ "$MODE" == "dev" ]; then
    print_info "Starting development server on http://localhost:$PORT"
    print_info "Press Ctrl+C to stop"
    echo ""
    python manage.py runserver 0.0.0.0:$PORT

elif [ "$MODE" == "prod" ]; then
    print_info "Starting production server with Gunicorn on port $PORT"
    print_info "Make sure Gunicorn is installed: pip install gunicorn"
    print_info "Press Ctrl+C to stop"
    echo ""
    
    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        print_error "Gunicorn is not installed"
        print_info "Install with: pip install gunicorn"
        exit 1
    fi
    
    GUNICORN_WORKERS=${3:-4}
    print_info "Starting with $GUNICORN_WORKERS workers"
    gunicorn FinAI.wsgi:application \
        --bind 0.0.0.0:$PORT \
        --workers $GUNICORN_WORKERS \
        --worker-class sync \
        --timeout 30 \
        --access-logfile - \
        --error-logfile -

elif [ "$MODE" == "setup" ]; then
    print_header "Setup Complete"
    print_success "Environment is ready!"
    echo ""
    echo "Next steps:"
    echo "  1. Update .env with your configuration"
    echo "  2. Run: ./run.sh dev     (development mode)"
    echo "  3. Or run: ./run.sh prod (production mode)"
    exit 0

elif [ "$MODE" == "migrate" ]; then
    # Migrations already done above, just show message
    print_header "Migrations Complete"
    print_success "Database is ready!"
    exit 0

elif [ "$MODE" == "shell" ]; then
    print_header "Django Shell"
    python manage.py shell_plus

elif [ "$MODE" == "help" ]; then
    print_header "FinAI Application Runner"
    echo ""
    echo "Usage: ./run.sh [MODE] [PORT] [OPTIONS]"
    echo ""
    echo "Modes:"
    echo "  dev      - Development server (default, hot-reload enabled)"
    echo "  prod     - Production server with Gunicorn"
    echo "  migrate  - Run database migrations only"
    echo "  shell    - Open Django shell"
    echo "  setup    - Setup and exit"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run.sh                    # Start dev server on port 8000"
    echo "  ./run.sh dev 3000           # Start dev server on port 3000"
    echo "  ./run.sh prod 8080 8        # Start prod server on port 8080 with 8 workers"
    echo "  ./run.sh migrate            # Run migrations only"
    echo ""
    echo "Environment variables (.env):"
    echo "  DEBUG                       - Django debug mode (True/False)"
    echo "  SECRET_KEY                  - Django secret key"
    echo "  DATABASE_*                  - Database configuration"
    echo "  OPENAI_API_KEY              - OpenAI API key (for Phase 5)"
    echo ""
    exit 0

else
    print_error "Unknown mode: $MODE"
    echo "Run './run.sh help' for available modes"
    exit 1
fi
