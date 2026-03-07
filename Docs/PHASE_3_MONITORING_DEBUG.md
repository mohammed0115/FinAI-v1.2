# Phase 3 Monitoring, Debugging & Production Guide

## Production Monitoring

### Key Metrics to Track

#### 1. Processing Performance
```bash
# Monitor Phase 3 processing time (should be <500ms main path)
SELECT 
  AVG(EXTRACT(EPOCH FROM (event_time - LAG(event_time) OVER (ORDER BY event_time)))) as phase3_duration_sec,
  MAX(EXTRACT(EPOCH FROM (event_time - LAG(event_time) OVER (ORDER BY event_time)))) as max_duration_sec
FROM audit_trails
WHERE event_type IN ('compliance_check', 'risk_score', 'audit_summary')
  AND created_at > NOW() - INTERVAL '24 hours';
```

#### 2. Compliance Check Results
```bash
# Check distribution of risk levels (should be mostly Low/Medium)
SELECT 
  risk_level,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as percentage
FROM extracted_data
WHERE extraction_status = 'extracted'
  AND extracted_at > NOW() - INTERVAL '7 days'
GROUP BY risk_level
ORDER BY 
  CASE risk_level 
    WHEN 'Low' THEN 1 
    WHEN 'Medium' THEN 2 
    WHEN 'High' THEN 3 
    WHEN 'Critical' THEN 4 
  END;
```

Expected output:
```
risk_level | count | percentage
Low        | 8542  | 85.4%
Medium     | 1204  | 12.0%
High       | 198   | 2.0%
Critical   | 56    | 0.6%
```

#### 3. Failed Compliance Checks
```bash
# Identify most common failures
SELECT 
  check_name,
  SUM((compliance_checks::jsonb ->> check_name)::jsonb ->> 'status' = 'INVALID') as invalid_count,
  SUM((compliance_checks::jsonb ->> check_name)::jsonb ->> 'status' = 'MISSING') as missing_count
FROM extracted_data
WHERE extraction_status = 'extracted'
  AND extracted_at > NOW() - INTERVAL '30 days'
GROUP BY check_name
ORDER BY (invalid_count + missing_count) DESC;
```

#### 4. OpenAI API Performance
```bash
# Track OpenAI summary generation success rate
SELECT 
  (audit_summary::jsonb ->> 'generated_by') as generator,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as percentage,
  ROUND(AVG(CASE WHEN (audit_summary::jsonb ->> 'generated_by') = 'openai' 
    THEN (EXTRACT(EPOCH FROM audit_completed_at) - EXTRACT(EPOCH FROM extraction_completed_at)) 
    ELSE NULL END), 2) as avg_openai_latency_sec
FROM extracted_data
WHERE extraction_status = 'extracted'
  AND audit_summary IS NOT NULL
  AND extracted_at > NOW() - INTERVAL '7 days'
GROUP BY (audit_summary::jsonb ->> 'generated_by');
```

Expected output:
```
generator   | count | percentage | avg_openai_latency_sec
openai      | 9500  | 99.0%      | 0.85
rule_based  | 100   | 1.0%       | 0.12  (fallback used)
```

#### 5. Audit Trail Event Distribution
```bash
# Verify all phases are being logged
SELECT 
  phase,
  event_type,
  COUNT(*) as event_count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM audit_trails
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY phase, event_type
ORDER BY phase, event_count DESC;
```

---

## Debugging Guide

### Issue 1: Risk Score Not Calculated

**Symptoms:**
- `risk_score` is NULL
- `risk_level` is NULL
- audit_summary is NULL

**Diagnosis:**
```bash
# Check Phase 3 processing status
SELECT 
  id,
  extraction_status,
  extraction_error,
  risk_score,
  compliance_checks,
  audit_completed_at
FROM extracted_data
WHERE id = '<extracted_data_id>'
LIMIT 1;
```

**Check logs:**
```bash
tail -100 /var/log/django/error.log | grep -i "phase3\|risk_score\|risk_scor"
```

**Common causes:**

1. **Phase 3 service not called**
   ```python
   # Check if process_compliance_and_audit() is being called
   # in invoice_processing_service.py line ~180
   
   result = invoice_phase3_service.process_compliance_and_audit(
       extracted_data=extracted_data,
       organization=organization
   )
   # If this line is missing, add it back
   ```

2. **Database transaction rolled back**
   ```python
   # Check error handling in invoice_phase3_service.py
   # Line ~210 has try/except
   # If exception raised here, whole transaction rolls back
   ```
   
   **Fix:** Check `extraction_error` field for error message

3. **OpenAI API key missing**
   ```bash
   # Verify env var is set
   echo $OPENAI_API_KEY
   # Should output: sk-....
   # If empty, set it: export OPENAI_API_KEY="sk-..."
   ```

4. **Compliance service misconfiguration**
   ```bash
   # Verify singleton is initialized
   python manage.py shell
   >>> from core.invoice_compliance_service import invoice_compliance_service
   >>> print(invoice_compliance_service)
   # Should print: <invoice_compliance_service.InvoiceComplianceService object at 0x...>
   ```

---

### Issue 2: Wrong Risk Level Assigned

**Symptoms:**
- `risk_level` is "Low" but should be "High"
- Score is correct, level mapping is wrong

**Debug:**
```python
# Check risk scoring logic in invoice_risk_scoring_service.py
# Lines 45-65 have the level assignment logic

# Test manually:
from core.invoice_risk_scoring_service import invoice_risk_scoring_service

# Create test compliance checks (failed critical checks)
test_checks = [
    {'check_name': 'vendor_presence', 'status': 'MISSING', 'severity': 'CRITICAL'},
    {'check_name': 'customer_presence', 'status': 'PASS', 'severity': 'INFO'},
]

score, level = invoice_risk_scoring_service.compute_risk_score(test_checks)
print(f"Score: {score}, Level: {level}")
# Expected: Score: 50, Level: Medium
```

**Weights verification:**
```python
# Check if weights are correct in invoice_risk_scoring_service.py
SEVERITY_WEIGHTS = {
    'INFO': 0,
    'WARNING': 10,
    'ERROR': 25,
    'CRITICAL': 50,  # This must be 50
}

STATUS_WEIGHTS = {
    'PASS': 0,
    'AVAILABLE': 5,
    'WARNING': 15,
    'INVALID': 25,
    'MISSING': 40,  # This must be 40
}
```

---

### Issue 3: Compliance Checks Incomplete

**Symptoms:**
- Only 5/9 checks executed
- `compliance_checks` array has fewer than 9 items

**Debug:**
```bash
# Check which check is failing
SELECT JSON_ARRAY_LENGTH(compliance_checks) as check_count
FROM extracted_data
WHERE extraction_status = 'extracted'
ORDER BY extracted_at DESC
LIMIT 5;
```

**Diagnosis:**
1. Check if exception occurred in middle of checks
2. Look for specific check method with error
3. Verify input data for that check

**Common causes:**

1. **Missing decimal library import**
   ```python
   # Line 1 of invoice_compliance_service.py
   from decimal import Decimal, InvalidOperation
   # Must be present
   ```

2. **Null reference in normalization**
   ```python
   # _check_total_consistency expects decimal parsing
   # If items aren't properly normalized, this fails
   
   # Test:
   check_service.check_invoice_compliance(extracted_data)
   # Will raise exception which shows which check failed
   ```

3. **Currency validation list incomplete**
   ```python
   # Valid currencies hardcoded in _check_currency_validity
   # If you added new currencies, update the list
   VALID_CURRENCIES = ['USD', 'EUR', 'GBP', 'AED', 'SAR', ...]
   ```

---

### Issue 4: Audit Summary is Rule-Based When it Should Be OpenAI

**Symptoms:**
- `audit_summary.generated_by` = "rule_based"
- Should be "openai"
- OpenAI API calls failing silently

**Debug:**
```python
# Check OpenAI call in invoice_audit_summary_service.py
# Lines 85-105 have the API call

# Manual test:
import os
import requests

api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("ERROR: OPENAI_API_KEY not set!")
else:
    # Make test call
    response = requests.post(
        'https://api.openai.com/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        },
        json={
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': 'test'}],
            'max_tokens': 100
        }
    )
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.text}")
```

**Common causes:**

1. **Invalid API key**
   ```bash
   # Check format
   echo $OPENAI_API_KEY | grep -E "^sk-"
   # Should match: sk-<40+ characters>
   ```

2. **Rate limiting or quota exceeded**
   ```
   Check OpenAI account for:
   - API usage quota
   - Rate limits (10,000 requests/min for gpt-3.5-turbo)
   - Account balance / payment method
   ```

3. **Network connectivity issue**
   ```bash
   # Test connectivity to OpenAI
   curl -v https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     2>&1 | grep "HTTP/1.1"
   # Should show: HTTP/1.1 200 or 400 (but not connection error)
   ```

4. **Timeout (processing takes >5 seconds)**
   ```python
   # In invoice_audit_summary_service.py, check timeout
   # Line ~90: timeout=5  # seconds
   # If invoices are complex, increase to 10
   ```

---

### Issue 5: Audit Trail Missing Events

**Symptoms:**
- Only 3/6 events in audit_trail
- Phase 3 events not logged

**Debug:**
```bash
# Check all events for a document
SELECT event_type, phase, success, event_time
FROM audit_trails
WHERE extracted_data_id = '<id>'
ORDER BY event_time;
```

**Expected sequence:**
```
Event 1: upload (NULL phase)
Event 2: extraction (phase1)
Event 3: normalization (phase2)
Event 4: validation (phase2)
Event 5: compliance_check (phase3)
Event 6: audit_summary (phase3)
Event 7: review (NULL phase) [optional, user-triggered]
Event 8: accept/reject/correct (NULL phase) [optional, user-triggered]
```

**If Phase 3 events missing:**

Check `_create_audit_trail_entry` in invoice_phase3_service.py

```python
# Around line 170-180, this should be called:
# Phase 3 service calls _create_audit_trail_entry()
# which creates AuditTrail model instance

# Verify it's being saved:
# Line ~180: audit_trail.save()
```

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] Database migrations applied (`python manage.py migrate documents`)
- [ ] Static files collected (`python manage.py collectstatic --noinput`)
- [ ] OPENAI_API_KEY configured in production environment
- [ ] Settings.py DEBUG = False
- [ ] ALLOWED_HOSTS configured correctly
- [ ] Email backend configured (for error alerts)
- [ ] Celery/beat configured (if async processing needed)

### Post-Deployment

- [ ] Health check endpoint responds (GET /health/)
- [ ] Document upload accepts files (POST /api/documents/upload/)
- [ ] Review endpoint returns Phase 3 data (GET /api/extracted-data/{id}/review/)
- [ ] Risk scores populated within 30 seconds of upload
- [ ] Audit summary generated (OpenAI or fallback)
- [ ] Audit trail has 6+ events for successful uploads
- [ ] Error handling working (test with invalid file)
- [ ] Database queries performing well (<100ms for review endpoint)

### Monitoring Setup

```bash
# 1. Application logs
tail -f /var/log/django/error.log | grep "phase3\|risk\|compliance"

# 2. Database performance
EXPLAIN ANALYZE SELECT * FROM extracted_data 
  WHERE extraction_status = 'extracted' 
  ORDER BY extracted_at DESC LIMIT 100;

# 3. OpenAI API usage
curl https://api.openai.com/v1/usage/tokens \
  -H "Authorization: Bearer $OPENAI_API_KEY" | jq '.data'

# 4. System resources (Phase 3 is low CPU/memory)
top -p $(pgrep -f manage.py) -b -n 1
# Should show: <5% CPU, <50MB memory per Phase 3 operation
```

---

## Performance Optimization

### If Phase 3 is Slow (>1 second)

1. **Cache compliance checks**
   ```python
   # In invoice_compliance_service.py, add caching:
   from functools import lru_cache
   
   @lru_cache(maxsize=1000)
   def _check_currency_validity(self, currency):
       # This check is deterministic, can cache
   ```

2. **Async OpenAI calls with Celery**
   ```python
   # Instead of:
   summary = openai_summary_service.generate(...)
   
   # Use:
   from celery import shared_task
   
   @shared_task
   def generate_summary_async(extracted_data_id):
       ...
   
   # Call it without blocking:
   generate_summary_async.delay(extracted_data_id)
   ```

3. **Batch compliance checks**
   ```python
   # Instead of calling check service 9 times
   # Do all 9 checks in one pass through data
   # Current implementation is already optimized
   ```

4. **Database indexing**
   ```sql
   -- Ensure these indexes exist for review queries:
   CREATE INDEX idx_extracted_data_status ON extracted_data(extraction_status);
   CREATE INDEX idx_extracted_data_risk_level ON extracted_data(risk_level);
   CREATE INDEX idx_audit_trail_type ON audit_trails(event_type);
   
   -- Check current indexes:
   SELECT * FROM pg_indexes WHERE tablename = 'extracted_data';
   ```

---

## Rollback Procedure

If Phase 3 has critical issues:

### Option 1: Disable Phase 3 (Temporary)
```python
# In invoice_processing_service.py, comment out Phase 3 call:
# Around line 185
# result = invoice_phase3_service.process_compliance_and_audit(...)
# → Set to: pass  # Phase 3 disabled
```

### Option 2: Revert Code
```bash
cd /home/mohamed/FinAI-v1.2/backend

# Git revert to previous commit:
git reset --hard HEAD~1

# Or manually delete new files:
rm -f core/invoice_compliance_service.py \
      core/invoice_risk_scoring_service.py \
      core/invoice_audit_summary_service.py \
      core/invoice_phase3_service.py

# Revert model changes:
git checkout documents/models.py
git checkout documents/views.py
git checkout documents/serializers.py
git checkout core/invoice_processing_service.py

# Restart:
supervisorctl restart gunicorn
```

### Option 3: Keep Code, Skip Execution
```python
# In invoice_phase3_service.py, wrap entire function:
def process_compliance_and_audit(self, extracted_data, organization):
    # Temporarily disable
    return {
        'compliance_checks': [],
        'risk_score': 0,
        'risk_level': 'Low',
        'audit_summary': {'final_status': 'UNKNOWN'}
    }
```

---

## FAQs

**Q: Why is compliance check X returning MISSING when the data exists?**
A: The normalization might not have extracted the field. Check `normalized_invoice` object to see what was parsed. May need to adjust extraction regex in normalization service.

**Q: Can I customize risk scoring weights?**
A: Yes, edit `SEVERITY_WEIGHTS` and `STATUS_WEIGHTS` dicts in `invoice_risk_scoring_service.py` lines 35-48. Change any value and restart Django.

**Q: How do I add a 10th compliance check?**
A: Add new method in `InvoiceComplianceService` following pattern of existing checks, add to `check_invoice_compliance()` method around line 50, and increment expected count.

**Q: Why are OpenAI summaries sometimes generic?**
A: You're hitting the fallback generator. Check logs for OpenAI error. Most common: API key invalid or quota exceeded. Fix key and retry document.

**Q: Can Phase 3 process run in background?**
A: Currently runs synchronously. To make async, wrap `invoice_phase3_service.process_compliance_and_audit()` in Celery task. Requires Celery broker (Redis/RabbitMQ).

**Q: How large can audit_trail grow?**
A: For moderate volume (1000 docs/day), ~14 events each = 14K rows/day. Manageable. Consider archiving old records quarterly.

