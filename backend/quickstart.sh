#!/bin/bash

# ============================================================================
# FinAI Quick Start Script
# Minimal setup for rapid development
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_header() {
    echo -e "${GREEN}===================================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}===================================================${NC}"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Get directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

print_header "FinAI Quick Start"

# Check .env
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    print_info "Creating .env from default template..."
    cp "$SCRIPT_DIR/.env" "$SCRIPT_DIR/.env.local" 2>/dev/null || print_info ".env template not found, creating basic one"
    cat > "$SCRIPT_DIR/.env" << 'EOF'
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=db.sqlite3
ALLOWED_HOSTS=localhost,127.0.0.1
OPENAI_API_KEY=sk-your-api-key
EOF
    print_success ".env created with defaults"
fi

# Setup venv
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/venv"
    print_success "Virtual environment created"
fi

# Activate
source "$SCRIPT_DIR/venv/bin/activate"
print_success "Virtual environment activated"

# Install deps
print_info "Installing dependencies..."
pip install --upgrade pip > /dev/null
pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null
print_success "Dependencies installed"

# Migrate
print_info "Running migrations..."
cd "$SCRIPT_DIR"
python manage.py migrate --noinput > /dev/null
print_success "Database migrated"

print_header "Ready to Start!"
echo ""
echo "Run the server with:"
echo "  source venv/bin/activate"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
