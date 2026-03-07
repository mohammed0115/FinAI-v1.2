#!/bin/bash
# FinAI Production Operations - Quick Reference Guide
# 
# This script provides quick access to common operations
# Usage: bash finai_ops.sh <command>

set -e

PROJECT_ROOT="/home/mohamed/FinAI-v1.2"
BACKEND="$PROJECT_ROOT/backend"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Commands
cmd_status() {
    print_header "System Status"
    
    # Check database
    if [ -f "$BACKEND/db.sqlite3" ]; then
        print_success "Database found"
        echo "  Path: $BACKEND/db.sqlite3"
        SIZE=$(du -h "$BACKEND/db.sqlite3" | cut -f1)
        echo "  Size: $SIZE"
    else
        print_error "Database not found"
    fi
    
    # Check migrations
    echo ""
    echo "Checking Django configuration..."
    cd "$BACKEND"
    python manage.py check
}

cmd_dashboard() {
    print_header "Real-time Operations Dashboard"
    cd "$BACKEND"
    python operations_dashboard.py
}

cmd_test() {
    print_header "Production Readiness Tests"
    cd "$BACKEND"
    python test_production_readiness.py
}

cmd_test_uploads() {
    print_header "Invoice Upload & Processing Test"
    cd "$BACKEND"
    python test_invoice_uploads.py
}

cmd_deploy() {
    print_header "Production Deployment"
    
    if [ ! -f "$BACKEND/deploy_production.sh" ]; then
        print_error "Deploy script not found"
        exit 1
    fi
    
    cd "$BACKEND"
    bash deploy_production.sh
}

cmd_start() {
    print_header "Starting FinAI Services"
    
    cd "$BACKEND"
    
    # Check if already running
    if pgrep -f "python manage.py runserver" > /dev/null; then
        print_warn "Development server already running"
        echo "  Kill with: pkill -f 'python manage.py runserver'"
    else
        print_success "Starting development server on port 8000"
        echo "  Access dashboard: http://localhost:8000/api/documents/dashboard/"
        echo "  Press Ctrl+C to stop"
        echo ""
        
        python manage.py runserver 0.0.0.0:8000
    fi
}

cmd_stop() {
    print_header "Stopping Services"
    
    if pgrep -f "python manage.py runserver" > /dev/null; then
        pkill -f "python manage.py runserver"
        print_success "Development server stopped"
    else
        print_warn "No development server running"
    fi
    
    # For production systemd service
    if systemctl is-active --quiet finai 2>/dev/null; then
        sudo systemctl stop finai
        print_success "Production service stopped"
    fi
}

cmd_logs() {
    print_header "Application Logs"
    
    if systemctl is-active --quiet finai 2>/dev/null; then
        echo "Production logs:"
        sudo journalctl -u finai -n 50 --no-pager
    else
        print_warn "Production service not running"
        echo "Development logs should be in console output"
    fi
}

cmd_performance() {
    print_header "Performance Metrics"
    cd "$BACKEND"
    python -c "
from core.performance_monitor import PerformanceMetrics
PerformanceMetrics.print_report()
"
}

cmd_config() {
    print_header "Configuration Summary"
    cd "$BACKEND"
    python -c "
from core.pipeline_config import print_config_summary
print_config_summary()
"
}

cmd_migrate() {
    print_header "Database Migration"
    cd "$BACKEND"
    
    echo "Running migrations..."
    python manage.py migrate --verbosity 2
    print_success "Migrations completed"
}

cmd_backup() {
    print_header "Create Database Backup"
    
    BACKUP_DIR="$PROJECT_ROOT/backups"
    mkdir -p "$BACKUP_DIR"
    
    BACKUP_FILE="$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sqlite3"
    cp "$BACKEND/db.sqlite3" "$BACKUP_FILE"
    
    print_success "Backup created"
    echo "  Location: $BACKUP_FILE"
    echo "  Size: $(du -h "$BACKUP_FILE" | cut -f1)"
}

cmd_restore() {
    print_header "Restore Database Backup"
    
    BACKUP_DIR="$PROJECT_ROOT/backups"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_error "No backups found"
        exit 1
    fi
    
    echo "Available backups:"
    ls -1h "$BACKUP_DIR"/db_*.sqlite3 | tail -10 | nl
    
    echo ""
    echo "Enter backup number to restore (or Ctrl+C to cancel):"
    read -r CHOICE
    
    BACKUP_FILE=$(ls -1 "$BACKUP_DIR"/db_*.sqlite3 | tail -10 | sed -n "${CHOICE}p")
    
    if [ -z "$BACKUP_FILE" ]; then
        print_error "Invalid selection"
        exit 1
    fi
    
    echo "Restoring from: $BACKUP_FILE"
    cp "$BACKUP_FILE" "$BACKEND/db.sqlite3"
    print_success "Database restored"
}

cmd_cleanup() {
    print_header "System Cleanup"
    
    cd "$BACKEND"
    
    echo "Cleaning up temporary files..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    
    print_success "Cleanup completed"
}

cmd_superuser() {
    print_header "Create Admin User"
    cd "$BACKEND"
    python manage.py createsuperuser
}

cmd_org() {
    print_header "Organization Management"
    cd "$BACKEND"
    python manage.py shell << EOF
from core.models import Organization

print("Current organizations:")
for org in Organization.objects.all():
    print(f"  - {org.name} (ID: {org.id})")

print("\nTo create new organization:")
print("  org = Organization.objects.create(name='Your Org')")
print("  org.save()")
EOF
}

cmd_view_invoices() {
    print_header "Invoice Listing"
    cd "$BACKEND"
    python manage.py shell << EOF
from documents.models import ExtractedData

print("Recent invoices:")
for inv in ExtractedData.objects.all().order_by('-created_at')[:10]:
    print(f"  Invoice: {inv.invoice_number}")
    print(f"    Vendor: {inv.vendor_name}")
    print(f"    Amount: {inv.total_amount} {inv.currency}")
    print(f"    Risk: {inv.risk_score}/100 ({inv.risk_level})")
    print(f"    Valid: {inv.is_valid}")
    print()
EOF
}

cmd_help() {
    cat << 'EOF'
FinAI Operations Quick Reference
=================================

Usage: bash finai_ops.sh <command> [options]

Common Commands:
  status          - Check system status and configuration
  dashboard       - View real-time operations dashboard
  test            - Run production readiness tests
  test-uploads    - Test invoice upload and processing
  start           - Start development server (port 8000)
  stop            - Stop running services
  logs            - View application logs
  
Configuration:
  config          - View current configuration
  performance     - View performance metrics
  
Database:
  migrate         - Run database migrations
  backup          - Create database backup
  restore         - Restore from backup
  superuser       - Create admin user
  org             - Manage organizations
  invoices        - List recent invoices
  
Maintenance:
  cleanup         - Clean temporary files
  deploy          - Run production deployment
  
Examples:
  bash finai_ops.sh status
  bash finai_ops.sh dashboard
  bash finai_ops.sh test
  bash finai_ops.sh start
  bash finai_ops.sh backup
  bash finai_ops.sh config

For detailed documentation, see:
  PRODUCTION_DEPLOYMENT_GUIDE.md

EOF
}

# Main
case "${1:-help}" in
    status)
        cmd_status
        ;;
    dashboard)
        cmd_dashboard
        ;;
    test)
        cmd_test
        ;;
    test-uploads)
        cmd_test_uploads
        ;;
    deploy)
        cmd_deploy
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    logs)
        cmd_logs
        ;;
    performance)
        cmd_performance
        ;;
    config)
        cmd_config
        ;;
    migrate)
        cmd_migrate
        ;;
    backup)
        cmd_backup
        ;;
    restore)
        cmd_restore
        ;;
    cleanup)
        cmd_cleanup
        ;;
    superuser)
        cmd_superuser
        ;;
    org)
        cmd_org
        ;;
    invoices)
        cmd_view_invoices
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac
