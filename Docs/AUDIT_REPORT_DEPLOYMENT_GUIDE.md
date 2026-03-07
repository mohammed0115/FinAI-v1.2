# FinAI Audit Report System - Production Deployment Guide

## 🚀 Pre-Deployment Checklist

### 1. System Verification
```bash
cd /home/mohamed/FinAI-v1.2/backend

# Check Django configuration
python manage.py check
# Expected: System check identified no issues (0 silenced)

# Run migrations
python manage.py migrate documents
# Expected: No migrations to apply (if migrations already run)

# Verify tables exist
python manage.py dbshell
# > SELECT name FROM sqlite_master WHERE type='table' AND name='documents_invoiceauditreport';
# > SELECT COUNT(*) FROM documents_invoiceauditreport;
```

### 2. Integration Testing
```bash
cd /home/mohamed/FinAI-v1.2

# Run end-to-end test
python test_audit_report_integration.py

# Expected output:
# ✅ Integration test completed successfully!
# Report generated with all 11 sections populated
```

### 3. API Testing
```bash
# Start development server
cd backend
python manage.py runserver

# In another terminal, test endpoints:
curl http://localhost:8000/api/documents/audit-reports/
# Expected: JSON response with list endpoint

curl http://localhost:8000/api/documents/audit-reports/statistics/
# Expected: Statistics object with counts
```

---

## 📋 Production Configuration

### Environment Variables
```bash
# .env or production settings
export DJANGO_SECRET_KEY="your-secret-key-here"
export DEBUG=False
export ALLOWED_HOSTS="yourdomain.com,www.yourdomain.com"

# Optional: OpenAI API for AI summaries
export OPENAI_API_KEY="sk-your-api-key-here"

# Database (if using PostgreSQL)
export DB_ENGINE="django.db.backends.postgresql"
export DB_NAME="finai_production"
export DB_USER="finai_user"
export DB_PASSWORD="secure-password"
export DB_HOST="localhost"
export DB_PORT="5432"
```

### Django Settings (`backend/FinAI/settings.py`)
```python
# Verify these settings for production:

# 1. Debug mode
DEBUG = False

# 2. Allowed hosts
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# 3. Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',  # Use PostgreSQL, not SQLite
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# 4. Static files
STATIC_ROOT = '/path/to/finai/staticfiles'
STATIC_URL = '/static/'

# 5. Media files
MEDIA_ROOT = '/path/to/finai/media'
MEDIA_URL = '/media/'

# 6. Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'"),
}

# 7. Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/finai/audit_reports.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

---

## 🗄️ Database Migration Path

### From SQLite to PostgreSQL (Optional)
```bash
# 1. Export SQLite data
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.Permission > db_backup.json

# 2. Update settings.py to use PostgreSQL
# (See above)

# 3. Run migrations
python manage.py migrate documents

# 4. Load data
python manage.py loaddata db_backup.json

# 5. Generate reports for existing data
python manage.py generate_audit_reports --all
```

---

## 🔄 Deployment Steps

### Step 1: Backup Current System
```bash
# Backup database
cp /path/to/db.sqlite3 /backup/db.sqlite3.$(date +%Y%m%d_%H%M%S)

# Backup media
tar -czf /backup/finai_media_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/media/
```

### Step 2: Pull Latest Code
```bash
cd /home/mohamed/FinAI-v1.2
git pull origin main
```

### Step 3: Update Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### Step 4: Run Migrations
```bash
cd backend
python manage.py migrate documents
```

### Step 5: Collect Static Files
```bash
cd backend
python manage.py collectstatic --noinput
```

### Step 6: Generate Reports for Existing Data
```bash
cd backend
# This will generate reports for all documents without reports
python manage.py generate_audit_reports --limit 100

# Continue with remaining:
python manage.py generate_audit_reports --limit 100

# To generate all:
python manage.py generate_audit_reports --all
```

### Step 7: Run System Checks
```bash
cd backend
python manage.py check
```

### Step 8: Restart Services
```bash
# If using Gunicorn
sudo systemctl restart finai-gunicorn
sudo systemctl restart finai-celery  # If using async tasks

# If using Docker
docker-compose restart web
```

### Step 9: Verify Deployment
```bash
# Check API endpoint
curl https://yourdomain.com/api/documents/audit-reports/

# Check Django admin
# Visit: https://yourdomain.com/admin/documents/invoiceauditreport/

# Monitor logs
tail -f /var/log/finai/audit_reports.log
```

---

## 🔐 Security Hardening

### 1. Database Encryption
```sql
-- PostgreSQL example
CREATE SCHEMA finai_audit;
GRANT USAGE ON SCHEMA finai_audit TO finai_user;

-- Enable SSL for connections
-- Update pg_hba.conf: hostssl all finai_user localhost md5
```

### 2. Access Control
```python
# In Django settings
# Role-based access control for reports

from rest_framework.permissions import IsAuthenticated, BasePermission

class AuditReportPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Users can only see reports from their organization
        return obj.organization == request.user.organization
```

### 3. Audit Logging
```python
# Add to signals.py to track all report operations
@receiver(pre_save, sender=InvoiceAuditReport)
def log_report_changes(sender, instance, **kwargs):
    AuditLog.objects.create(
        user=instance.generated_by,
        action='REPORT_GENERATED',
        model='InvoiceAuditReport',
        object_id=instance.id
    )
```

### 4. Data Masking
```python
# Mask sensitive data in API responses
class AuditReportSerializer(serializers.ModelSerializer):
    extracted_vendor_tin = serializers.SerializerMethodField()
    
    def get_extracted_vendor_tin(self, obj):
        if obj.extracted_vendor_tin:
            # Show only last 4 digits
            return '****' + obj.extracted_vendor_tin[-4:]
        return None
```

---

## 📊 Monitoring & Performance

### 1. Performance Metrics
```python
# Add to views.py to track performance
import time
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

class InvoiceAuditReportViewSet(ReadOnlyModelViewSet):
    @method_decorator(cache_page(60))  # Cache for 1 minute
    def list(self, request, *args, **kwargs):
        start = time.time()
        response = super().list(request, *args, **kwargs)
        duration = time.time() - start
        print(f"Report list API took {duration:.2f}s")
        return response
```

### 2. Database Query Monitoring
```python
# Install django-debug-toolbar for development
pip install django-debug-toolbar

# Or use django-silk for production
pip install django-silk
```

### 3. Error Tracking
```python
# Configure Sentry for error tracking
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="https://your-sentry-dsn@sentry.io/project-id",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    environment="production"
)
```

### 4. Real-time Monitoring
```bash
# Monitor report generation in real-time
cd backend
tail -f /var/log/finai/audit_reports.log | grep "Report generated"
```

---

## 🚨 Troubleshooting

### Issue 1: Reports Not Auto-Generating
**Symptoms**: Upload document, ExtractedData created, but no report
**Solution**:
```python
# Check signal is registered
from django.core.signals import post_save
print(post_save.receivers)  # Should include auto_generate_audit_report

# Check app is in INSTALLED_APPS
python manage.py check

# Manually trigger
from documents.models import ExtractedData
extracted = ExtractedData.objects.latest('created_at')
from documents.services import InvoiceAuditReportService
service = InvoiceAuditReportService(user=extracted.document.uploaded_by)
service.generate_comprehensive_report(
    extracted_data=extracted,
    document=extracted.document,
    organization=extracted.document.organization
)
```

### Issue 2: API Returns 404
**Symptoms**: `curl http://localhost:8000/api/documents/audit-reports/` returns 404
**Solution**:
```python
# Check URLs are registered
from django.urls import resolve
match = resolve('/api/documents/audit-reports/')
print(match.func)  # Should be ViewSet list method

# Check ViewSet is registered
python manage.py show_urls | grep audit-reports
```

### Issue 3: Database Constraint Error
**Symptoms**: `UNIQUE constraint failed: documents_extracteddata.document_id`
**Solution**:
```python
# This happens when signal tries to create ExtractedData that already exists
# Solution in signal handler:
extracted_data, created = ExtractedData.objects.get_or_create(
    document=instance.document,
    defaults={...}
)
```

### Issue 4: OpenAI API Errors
**Symptoms**: AI summaries fail, but reports still generate
**Solution**:
```python
# Add back fallback handling to openai_service.py
try:
    response = openai.ChatCompletion.create(...)
except Exception as e:
    logger.warning(f"OpenAI API error: {e}, using fallback")
    return generate_fallback_summary()
```

---

## 📈 Scaling Considerations

### 1. High-Volume Processing
```python
# Use Celery for async report generation
from celery import shared_task

@shared_task
def generate_report_async(extracted_data_id):
    from documents.models import ExtractedData
    from documents.services import InvoiceAuditReportService
    
    extracted = ExtractedData.objects.get(id=extracted_data_id)
    service = InvoiceAuditReportService(user=extracted.document.uploaded_by)
    return service.generate_comprehensive_report(extracted_data=extracted, ...)

# In signals.py
@receiver(post_save, sender=ExtractedData)
def auto_generate_audit_report(sender, instance, created, **kwargs):
    if created:
        generate_report_async.delay(instance.id)
```

### 2. Database Optimization
```python
# Add indexes for performance
class InvoiceAuditReport(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['risk_level']),
            models.Index(fields=['status']),
            models.Index(fields=['organization', 'created_at']),
        ]
```

### 3. Caching Strategy
```python
# Cache report statistics
from django.views.decorators.cache import cache_page

@cache_page(300)  # Cache for 5 minutes
def statistics(self, request):
    # Returns cached statistics
```

---

## 🔄 Maintenance & Updates

### Weekly Tasks
```bash
# Monitor report generation
python manage.py dbshell
SELECT COUNT(*) FROM documents_invoiceauditreport;
SELECT risk_level, COUNT(*) FROM documents_invoiceauditreport 
GROUP BY risk_level;

# Check logs for errors
grep ERROR /var/log/finai/audit_reports.log | tail -20
```

### Monthly Tasks
```bash
# Generate reports for new documents
python manage.py generate_audit_reports

# Vacuum database
python manage.py dbshell
# VACUUM;

# Backup database
mysqldump -u user -p finai_db > backup_$(date +%Y%m%d).sql
```

### Quarterly Tasks
```bash
# Review and update validation rules
# Review duplicate detection thresholds
# Update risk scoring weights
# Audit approval recommendations
```

---

## 📞 Support & Escalation

### For API Issues
1. Check logs: `/var/log/finai/audit_reports.log`
2. Run system check: `python manage.py check`
3. Test endpoint: `curl -v http://localhost:8000/api/documents/audit-reports/`

### For Report Generation Issues
1. Check signal trigger: Verify ExtractedData creation triggers report
2. Verify service: Manually run `generate_comprehensive_report()`
3. Check dependencies: Verify OpenAI API key (if using AI features)

### For Performance Issues
1. Monitor database queries: Enable query logging
2. Check report generation time: Should be <500ms
3. Scale horizontally: Add more workers if using Celery

### For Data Issues
1. Validate input data: Check OCREvidence and ExtractedData
2. Run corrective reports: `generate_audit_reports --all`
3. Review audit trail: Check full_report_json for processing history

---

## ✅ Deployment Checklist

- [ ] Database backed up
- [ ] Code pulled to production
- [ ] Dependencies installed
- [ ] Migrations run successfully
- [ ] System check passes (0 issues)
- [ ] Static files collected
- [ ] API endpoints responding
- [ ] Reports generating automatically
- [ ] Historical data processed: `generate_audit_reports --all`
- [ ] Admin interface working
- [ ] Logs configured and monitored
- [ ] Security settings hardened
- [ ] SSL certificates valid
- [ ] CDN configured (if using)
- [ ] Email notifications working (if configured)
- [ ] Monitoring alerts set up
- [ ] Backup procedure verified
- [ ] Disaster recovery plan tested

---

## 🎯 Success Criteria

✅ System deployed successfully when:
- Django check shows 0 issues
- API endpoints returning 200 OK
- Reports auto-generating on document upload
- Historical reports generated for existing data
- Performance acceptable (<500ms per report)
- Zero errors in logs over 24 hours
- All monitoring alerts configured
- Team trained on new features

---

## 📱 Post-Deployment Support

**First Week**:
- Monitor error logs closely
- Test with sample data
- Collect user feedback
- Make any necessary adjustments

**Second Week**:
- Generate full historical data batch
- Verify all reports display correctly
- Test API integrations
- Collect performance metrics

**Third Week+**:
- Ongoing monitoring
- Regular maintenance routines
- Performance tuning
- Feature enhancements based on feedback

---

**Deployment Version**: 1.0.0  
**Last Updated**: March 7, 2026  
**Status**: ✅ Ready for Production
