# FinAI Production Deployment & Operations Guide

Complete guide for deploying FinAI to production and monitoring system performance.

## Quick Start (5 minutes)

```bash
# 1. Configure environment
export OPENAI_API_KEY="sk-..."
export DEBUG=False

# 2. Run pre-deployment checks
cd backend
python test_production_readiness.py

# 3. Deploy
bash deploy_production.sh

# 4. Test with sample invoice
python test_invoice_uploads.py

# 5. Monitor performance
python -c "from core.performance_monitor import PerformanceMetrics; print(PerformanceMetrics.print_report())"
```

---

## Phase 1: Pre-Deployment Configuration

### 1.1 Environment Variables

Create `.env` or set in your deployment environment:

```bash
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=sk-your-actual-key-here
OPENAI_EXTRACTION_MODEL=gpt-4o-mini           # Default: gpt-4o-mini
OPENAI_NARRATIVE_MODEL=gpt-3.5-turbo          # Default: gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7                         # Default: 0.7 (0.0-1.0)
OPENAI_TIMEOUT=30                              # Default: 30 seconds
OPENAI_MAX_RETRIES=3                           # Default: 3 retries

# Django Configuration
DEBUG=False                                     # Always False for production
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_NAME=/path/to/db.sqlite3
DATABASE_PASSWORD=your-db-password

# Compliance Configuration
COMPLIANCE_DISCOUNT_THRESHOLD=0.20             # 20% suspicious discount
COMPLIANCE_LARGE_INVOICE_THRESHOLD=100000      # 100,000 SAR
COMPLIANCE_VERY_LARGE_THRESHOLD=1000000        # 1,000,000 SAR
COMPLIANCE_TAX_ID_REQUIRED=True

# Cross-Document Configuration
CROSS_DOC_EXACT_MATCH_THRESHOLD=0.99           # 99% similarity = exact duplicate
CROSS_DOC_HIGH_SIMILARITY_THRESHOLD=0.85       # 85% similarity threshold
CROSS_DOC_SPIKE_RATIO=2.0                      # 200% increase triggers anomaly
CROSS_DOC_STALE_DAYS=180                       # Invoices older than 180 days flagged

# Financial Configuration
FINANCIAL_FORECAST_DAYS=90                     # 90-day cash flow forecast
FINANCIAL_SPEND_MONTHS=12                      # 12-month spending analysis
FINANCIAL_TREND_THRESHOLD=0.10                 # 10% trend change

# Performance Configuration
PERFORMANCE_ENABLE_PROFILING=False             # Set True to collect metrics
PERFORMANCE_VERBOSE_LOGGING=False              # Set True for detailed logs
```

### 1.2 Verification Checklist

Run pre-deployment tests:

```bash
cd backend
python test_production_readiness.py
```

Expected output:
```
TEST 1: Configuration Verification        ✓ PASS
TEST 2: Pipeline Services Import         ✓ PASS
TEST 3: Database Access                  ✓ PASS
TEST 4: Dashboard View Access            ✓ PASS
TEST 5: Sample Invoice Processing        ✓ PASS
TEST 6: Performance Monitoring Setup      ✓ PASS

✓ ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION
```

---

## Phase 2: Database Setup

### 2.1 Initialize Database

```bash
cd backend

# Create migrations (if needed)
python manage.py makemigrations

# Apply migrations
python manage.py migrate --verbosity 2

# Create default organization (if new install)
python manage.py shell
>>> from core.models import Organization
>>> org, created = Organization.objects.get_or_create(name='Default Organization')
>>> print(f"Organization: {org.name} (ID: {org.id})")
>>> exit()

# Create admin user (if new install)
python manage.py createsuperuser
```

### 2.2 Database Schema

Key tables for invoice processing:

- **documents_document** - Uploaded invoice files
- **documents_extracteddata** - Extraction results across all 5 phases
- **documents_anomalylog** - Detected anomalies
- **documents_crossdocumentfinding** - Cross-document analysis results
- **documents_cashflowforecast** - Financial forecasts
- **core_organization** - Organizations
- **auth_user** - Users with roles

### 2.3 Database Backup

```bash
# SQLite backup
cp backend/db.sqlite3 backend/db.sqlite3.backup.$(date +%Y%m%d)

# PostgreSQL backup (if using PostgreSQL)
pg_dump finai_db > finai_backup_$(date +%Y%m%d).sql

# Restore from backup
psql finai_db < finai_backup_YYYYMMDD.sql
```

---

## Phase 3: Deployment Options

### 3.1 Development Server (Testing Only)

```bash
cd backend
export DJANGO_SETTINGS_MODULE=FinAI.dev
python manage.py runserver 0.0.0.0:8000
```

Access: `http://localhost:8000/api/documents/dashboard/`

### 3.2 Production Deployment (Gunicorn + Nginx)

#### Step 1: Install Gunicorn

```bash
pip install gunicorn
```

#### Step 2: Create Gunicorn Config

Create `backend/gunicorn_config.py`:

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
daemon = False

# Logging
accesslog = "/var/log/gunicorn_access.log"
errorlog = "/var/log/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "finai"
```

#### Step 3: Create Systemd Service

Create `/etc/systemd/system/finai.service`:

```ini
[Unit]
Description=FinAI Financial Document Analysis
After=network.target

[Service]
User=finai
WorkingDirectory=/path/to/FinAI-v1.2/backend
ExecStart=/usr/bin/gunicorn \
    --config gunicorn_config.py \
    --env DJANGO_SETTINGS_MODULE=FinAI.prod \
    FinAI.wsgi:application

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### Step 4: Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable finai
sudo systemctl start finai
sudo systemctl status finai

# View logs
sudo journalctl -u finai -f
```

#### Step 5: Configure Nginx

Create `/etc/nginx/sites-available/finai`:

```nginx
upstream finai_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    client_max_body_size 50M;

    location /static/ {
        alias /path/to/FinAI-v1.2/backend/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /path/to/FinAI-v1.2/backend/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://finai_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        proxy_connect_timeout 90;
    }

    # SSL (optional - use Let's Encrypt)
    # listen 443 ssl;
    # ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/finai /etc/nginx/sites-enabled/finai
sudo nginx -t
sudo systemctl restart nginx
```

### 3.3 Using Docker (Recommended)

```bash
# Build image
docker build -t finai:latest .

# Run container
docker run -d \
  --name finai \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e DEBUG=False \
  -v /data/db:/app/backend/data \
  -v /data/media:/app/backend/media \
  finai:latest

# View logs
docker logs -f finai

# Backup database
docker cp finai:/app/backend/data/db.sqlite3 ./db.sqlite3.backup
```

---

## Phase 4: Invoice Upload & Testing

### 4.1 Upload through Dashboard

1. Navigate to: `http://yourserver/api/documents/dashboard/`
2. Click "Upload Invoice"
3. Select PDF or image file
4. System processes through 5 phases automatically

### 4.2 API Upload

```bash
curl -X POST http://yourserver/api/documents/upload/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@invoice.pdf"
```

### 4.3 Test Suite

```bash
# Run complete test (creates sample invoices)
cd backend
python test_invoice_uploads.py

# Output will show:
# - Upload status
# - Phase-by-phase processing results
# - Dashboard verification
# - Performance metrics
```

### 4.4 Sample Test Data

Pre-populated sample invoice:
- Invoice #: INV-2024-001
- Vendor: ABC Supplies Co.
- Amount: 15,000 SAR
- Risk Score: 18/100 (Low Risk)
- Status: All 5 phases completed, validation passed

Access: `http://yourserver/api/documents/invoice/1/`

---

## Phase 5: Configuration & Customization

### 5.1 Compliance Thresholds

Edit `backend/core/pipeline_config.py`:

```python
class ComplianceConfig:
    # Adjust suspicious discount threshold (0.0-1.0)
    SUSPICIOUS_DISCOUNT_THRESHOLD = 0.20  # 20%
    
    # Large invoice threshold in SAR
    LARGE_INVOICE_THRESHOLD = 100000
    VERY_LARGE_INVOICE_THRESHOLD = 1000000
    
    # Flag invoices without tax ID
    REQUIRE_TAX_ID = True
    
    # Payment terms validation
    ACCEPTABLE_PAYMENT_TERMS = {
        'net_0': 0,
        'net_30': 30,
        'net_60': 60,
        'net_90': 90,
        'net_120': 120,
        'net_180': 180,
    }
```

Or via environment variables:

```bash
export COMPLIANCE_DISCOUNT_THRESHOLD=0.25
export COMPLIANCE_LARGE_INVOICE_THRESHOLD=150000
```

### 5.2 Cross-Document Analysis

Edit `backend/core/pipeline_config.py`:

```python
class CrossDocumentConfig:
    # Exact duplicate threshold
    EXACT_MATCH_THRESHOLD = 0.99  # 99% similarity
    
    # High similarity warning
    HIGH_SIMILARITY_THRESHOLD = 0.85  # 85% similarity
    
    # Sudden spike detection
    SUDDEN_SPIKE_RATIO = 2.0  # 200% increase flags anomaly
    
    # Stale invoice detection
    STALE_INVOICE_DAYS = 180  # 6 months
```

### 5.3 Financial Configuration

```python
class FinancialConfig:
    # Cash flow forecast period (days)
    FORECAST_PERIOD_DAYS = 90
    
    # Spending analysis lookback (months)
    SPEND_ANALYSIS_MONTHS = 12
    
    # Trend change threshold for alerts
    SPENDING_TREND_THRESHOLD = 0.10  # 10%
```

### 5.4 OpenAI Configuration

```python
class OpenAIConfig:
    EXTRACTION_MODEL = 'gpt-4o-mini'  # Fastest, good accuracy
    # Alternative: 'gpt-4o' (better accuracy, slower)
    # Alternative: 'gpt-4' (most accurate, much slower)
    
    NARRATIVE_MODEL = 'gpt-3.5-turbo'
    TEMPERATURE = 0.7  # Lower = more deterministic (0.0-1.0)
    TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
```

---

## Phase 6: Performance Monitoring

### 6.1 Enable Performance Tracking

```bash
export PERFORMANCE_ENABLE_PROFILING=True
export PERFORMANCE_VERBOSE_LOGGING=True
```

### 6.2 View Performance Metrics

```bash
cd backend
python -c "
from core.performance_monitor import PerformanceMetrics
PerformanceMetrics.print_report()
"
```

Expected output:

```
PERFORMANCE REPORT
==================

Metric: invoice_extraction
  - Executions: 42
  - Last: 8.32s
  - Min: 6.21s
  - Max: 12.45s
  - Avg: 8.75s
  - Total: 367.5s

Metric: compliance_check
  - Executions: 42
  - Last: 1.05s
  - Min: 0.89s
  - Max: 1.89s
  - Avg: 1.12s
  - Total: 47.0s
```

### 6.3 Monitor System Resources

```bash
# Watch CPU and memory
watch -n 1 'ps aux | grep gunicorn | head -5'

# Monitor database
sqlite3 backend/db.sqlite3 "SELECT COUNT(*) FROM documents_document;"
sqlite3 backend/db.sqlite3 "SELECT COUNT(*) FROM documents_extracteddata;"

# Check disk usage
du -sh /path/to/FinAI-v1.2/backend/media/*
```

### 6.4 Application Logging

Enable application logging:

```python
# In FinAI/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/finai.log',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

View logs:

```bash
tail -f /var/log/finai.log
tail -f /var/log/gunicorn_error.log
```

---

## Phase 7: Troubleshooting

### Issue: OpenAI API errors

**Symptoms**: "Failed to extract invoice", timeouts

**Solutions**:
```bash
# Check API key
echo $OPENAI_API_KEY | cut -c1-10,50-

# Test directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check quota: https://platform.openai.com/account/usage

# Increase timeout
export OPENAI_TIMEOUT=60
```

### Issue: Slow processing

**Symptoms**: Dashboard shows "Processing..." for > 1 minute

**Solutions**:
```bash
# Check performance metrics
python -c "from core.performance_monitor import PerformanceMetrics; print(PerformanceMetrics.print_report())"

# Monitor OpenAI API
tail -f /var/log/finai.log | grep "openai"

# Try faster model
export OPENAI_EXTRACTION_MODEL=gpt-3.5-turbo

# Reduce batch size
export BATCH_SIZE=5
```

### Issue: Database connection errors

**Symptoms**: "Could not connect to database"

**Solutions**:
```bash
# Check database file
ls -lh backend/db.sqlite3

# Verify permissions
chmod 666 backend/db.sqlite3

# Reset database (CAREFUL!)
rm backend/db.sqlite3
python manage.py migrate

# Check PostgreSQL (if using)
psql -l
```

### Issue: Dashboard not loading

**Symptoms**: HTTP 404 or 500 on `/api/documents/dashboard/`

**Solutions**:
```bash
# Check URL routing
python manage.py show_urls | grep dashboard

# Verify migrations applied
python manage.py showmigrations

# Restart service
sudo systemctl restart finai

# Check logs
sudo journalctl -u finai -n 50
```

---

## Phase 8: Maintenance & Backups

### 8.1 Regular Backups

```bash
#!/bin/bash
BACKUP_DIR="/backups/finai"
mkdir -p $BACKUP_DIR

# Daily backup
BACKUP_FILE="$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sqlite3"
cp /path/to/FinAI-v1.2/backend/db.sqlite3 "$BACKUP_FILE"

# Keep only last 7 days
find $BACKUP_DIR -name "db_*.sqlite3" -mtime +7 -delete

echo "Backup saved: $BACKUP_FILE"
```

Add to crontab for daily backups:

```bash
0 2 * * * /path/to/backup_finai.sh
```

### 8.2 Database Maintenance

```bash
# Run weekly
cd backend

# Optimize database
python manage.py dbshell
VACUUM;
ANALYZE;
.quit

# Clear old logs
python manage.py cleanupsessions
```

### 8.3 Update Dependencies

```bash
# Check for updates
cd backend
pip list --outdated

# Update
pip install --upgrade -r requirements.txt

# Test
python manage.py check
```

---

## Phase 9: Dashboard Endpoints

### Dashboard Views

- **Dashboard**: `GET /api/documents/dashboard/`
  - Statistics: total invoices, risk metrics, compliance rates
  - Recent invoices list (last 10)
  - Phase statistics for all 5 phases

- **Invoice Detail**: `GET /api/documents/invoice/<id>/`
  - All extracted data
  - All 5 phase results
  - Compliance checks detail
  - Cross-document analysis
  - Financial intelligence predictions

### API Endpoints

- **Upload Invoice**: `POST /api/documents/upload/`
  - Request: multipart/form-data with 'file'
  - Response: {document_id, status, processing_queue_position}

- **Invoice Status**: `GET /api/documents/<id>/status/`
  - Response: {extraction_status, phase1, phase2, phase3, phase4, phase5}

---

## Production Checklist

- [ ] Environment variables configured (OpenAI key, DEBUG=False)
- [ ] Database migrations applied
- [ ] Pre-deployment tests pass (`python test_production_readiness.py`)
- [ ] Admin user created (`python manage.py createsuperuser`)
- [ ] Default organization created
- [ ] Static files collected (`python manage.py collectstatic`)
- [ ] Gunicorn/Nginx configured
- [ ] SSL certificate installed (optional but recommended)
- [ ] Backup system configured
- [ ] Monitoring/logging enabled
- [ ] Sample invoice tested successfully
- [ ] Dashboard accessible and showing results
- [ ] Performance baseline established
- [ ] Disaster recovery plan documented

---

## Support & Maintenance

**For Issues**:
1. Run `python test_production_readiness.py` to diagnose
2. Check logs: `sudo journalctl -u finai -f`
3. Review configuration: `python backend/core/pipeline_config.py`
4. Test pipeline directly: `python test_invoice_uploads.py`

**For Performance Optimization**:
1. Monitor metrics: `PerformanceMetrics.print_report()`
2. Adjust batch sizes and timeouts
3. Consider upgrading to `gpt-4o` for better accuracy
4. Increase worker count in gunicorn_config.py

**For Customization**:
1. Edit `pipeline_config.py` for thresholds
2. Update compliance rules in `compliance_findings_service.py`
3. Add custom vendor risk rules in `cross_document_service.py`
4. Customize financial forecasts in `financial_intelligence_service.py`

---

**Last Updated**: 2024-12-18
**Version**: 1.2 Production Ready
**Python**: 3.12.3
**Django**: 5.0.1
