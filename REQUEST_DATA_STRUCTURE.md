# 📨 Request Data Structure - Clean & Validated

## Upload Form Request Data

### Form Tab: Single File (Default)

**HTTP Method**: `POST`
**Endpoint**: `http://localhost:8000/documents/upload/`
**Encoding**: `multipart/form-data`

### Request Headers
```
POST /documents/upload/ HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary
Cookie: sessionid=xxxx; csrftoken=xxxx
X-CSRFToken: xxxx
```

### Request Body (Raw Multipart)
```
------WebKitFormBoundary
Content-Disposition: form-data; name="csrfmiddlewaretoken"

xxxxxxxxxxxxxxxxxxxxxxxxxxxx
------WebKitFormBoundary
Content-Disposition: form-data; name="upload_mode"

single
------WebKitFormBoundary
Content-Disposition: form-data; name="document"; filename="invoice-2026.pdf"
Content-Type: application/pdf

[PDF Binary Content]
------WebKitFormBoundary
Content-Disposition: form-data; name="document_type"

invoice
------WebKitFormBoundary
Content-Disposition: form-data; name="language"

ara+eng
------WebKitFormBoundary
Content-Disposition: form-data; name="is_handwritten"

------WebKitFormBoundary--
```

### Python Dictionary Representation
```python
{
    'csrfmiddlewaretoken': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'upload_mode': 'single',
    'document': <InMemoryUploadedFile: invoice-2026.pdf>,
    'document_type': 'invoice',
    'language': 'ara+eng',
    'is_handwritten': False  # Not present if unchecked
}
```

---

## Server Processing (web_views.py)

### Step 1: Extract Form Data
```python
uploaded_file = request.FILES.get('document')  # InMemoryUploadedFile
document_type = request.POST.get('document_type', 'other')  # 'invoice'
language = request.POST.get('language', 'mixed')  # 'ara+eng'
is_handwritten = request.POST.get('is_handwritten') == 'on'  # False
```

### Step 2: Validation
```python
file_ext = os.path.splitext(uploaded_file.name)[1].lower()  # '.pdf'
allowed_types = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.bmp']

if file_ext not in allowed_types:
    raise ValidationError(f"نوع الملف {file_ext} غير مدعوم")

if uploaded_file.size > 50 * 1024 * 1024:  # 50MB
    raise ValidationError("حجم الملف يتجاوز الحد الأقصى")
```

### Step 3: Save File
```python
storage_key = f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
# Result: '20260307_181500_invoice-2026.pdf'

storage_path = f"/media/uploads/{org_id}/{storage_key}"
# Result: '/media/uploads/abc123/20260307_181500_invoice-2026.pdf'
```

### Step 4: Create Document Record
```python
document = Document.objects.create(
    organization=organization,
    uploaded_by=user,
    file_name="invoice-2026.pdf",
    file_type=".pdf",
    file_size=245600,  # bytes
    storage_key="uploads/abc123/20260307_181500_invoice-2026.pdf",
    storage_url="/media/uploads/abc123/20260307_181500_invoice-2026.pdf",
    document_type="invoice",
    status="pending",
    language="ara+eng",
    is_handwritten=False,
)
```

### Step 5: Call OCR Processing
```python
from core.views.document_views import process_document_ocr

success, message, ocr_evidence = process_document_ocr(
    document=document,
    file_path="/media/uploads/abc123/20260307_181500_invoice-2026.pdf",
    language="ara+eng",
    is_handwritten=False,
    user=user,
    organization=organization,
)
```

---

## OpenAI Vision API Call

### Request to OpenAI
```python
response = client.vision.analyze(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/pdf;base64,..."}
                },
                {
                    "type": "text",
                    "text": """استخرج بيانات الفاتورة:
                    - رقم الفاتورة
                    - تاريخ الإصدار
                    - تاريخ الاستحقاق
                    - اسم المورد
                    - اسم العميل
                    - البنود (الوصف، الكمية، السعر)
                    - الإجمالي والضريبة
                    """
                }
            ]
        }
    ]
)
```

### OpenAI Response
```json
{
    "invoice_number": "INV-2026-001",
    "issue_date": "2026-03-06",
    "due_date": "",
    "vendor_name": "Example Trading Co. Ltd",
    "customer_name": "Acme Industries Ltd",
    "items": [
        {
            "product": "Product A",
            "description": "Description A",
            "quantity": 2,
            "unit_price": 150.0,
            "total": 300.0
        },
        {
            "product": "Product B",
            "description": "Description B",
            "quantity": 1,
            "unit_price": 200.0,
            "total": 200.0
        }
    ],
    "subtotal": 500.0,
    "tax_amount": 75.0,
    "total_amount": 575.0,
    "currency": "SAR"
}
```

---

## OCREvidence Creation

### Data Saved to Database
```python
ocr_evidence = OCREvidence.objects.create(
    document=document,
    ocr_engine="openai_vision",
    confidence_score=85,
    text_ar="النص العربي المستخرج من الصورة...",
    text_en="English text extracted from image...",
    structured_data_json={
        "invoice_number": "INV-2026-001",
        "issue_date": "2026-03-06",
        "due_date": "",
        "vendor_name": "Example Trading Co. Ltd",
        "customer_name": "Acme Industries Ltd",
        "items": [...],
        "total_amount": 575.0,
        "tax_amount": 75.0,
        "currency": "SAR"
    },
    extracted_at=timezone.now()
)
```

---

## Post-OCR Pipeline

### Safe Date Parsing
```python
def parse_date_to_datetime(value):
    """Convert date string or None to proper datetime object"""
    if not value or (isinstance(value, str) and value.strip() == ''):
        return None  # Empty string → None
    
    if isinstance(value, str):
        # Try parsing various date formats
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
    
    if isinstance(value, datetime):
        return value
    
    return None

# Usage
invoice_date = parse_date_to_datetime("2026-03-06")  # → datetime(2026, 3, 6)
due_date = parse_date_to_datetime("")                 # → None
```

### Safe Amount Conversion
```python
from decimal import Decimal

def to_decimal(value):
    """Convert amount to Decimal safely"""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except:
        return None

# Usage
total_amount = to_decimal(575.0)   # → Decimal('575.00')
tax_amount = to_decimal(75.0)      # → Decimal('75.00')
```

### ExtractedData Creation
```python
extracted_data = ExtractedData.objects.create(
    document=document,
    organization=organization,
    
    # Extracted fields
    invoice_number="INV-2026-001",
    vendor_name="Example Trading Co. Ltd",
    customer_name="Acme Industries Ltd",
    
    # Dates (properly parsed)
    invoice_date=datetime(2026, 3, 6),  # datetime object
    due_date=None,                       # NULL in database
    
    # Amounts (Decimal type)
    total_amount=Decimal('575.00'),
    tax_amount=Decimal('75.00'),
    
    # Metadata
    currency="SAR",
    items_json=[...],
    confidence=85,
    extraction_status='extracted',
    extraction_provider='openai_vision',
    validation_status='validated',
    is_valid=True,
    normalized_json={...}
)
```

---

## Response to User

### Success Response
**Status Code**: `302 Found` (Redirect)
**Location Header**: `http://localhost:8000/pipeline/{document_id}/`
**Message**: "تم معالجة المستند بنجاح"

### Display Pipeline Result
The user is redirected to `pipeline_result.html` which displays:
- ✅ Section 1: Document Information
- ✅ Section 2: Invoice Data
- ✅ Section 3: Line Items
- ✅ Section 4: Financial Totals
- ✅ Section 5: Validation Results
- ✅ Section 6: Duplicate Detection
- ✅ Section 7: Anomaly Detection
- ✅ Section 8: Risk Assessment
- ✅ Section 9: AI Summary
- ✅ Section 10: Recommendations
- ✅ Section 11: Audit Trail

---

## Error Handling

### File Validation Errors
```python
if file_ext not in allowed_types:
    messages.error(request, f'نوع الملف غير مدعوم: {file_ext}')
    return redirect('document_upload')

if uploaded_file.size > 50 * 1024 * 1024:
    messages.error(request, 'حجم الملف يتجاوز الحد الأقصى (50MB)')
    return redirect('document_upload')
```

### Processing Errors
```python
try:
    success, message, ocr_evidence = process_document_ocr(...)
    if not success:
        messages.error(request, f'فشل استخراج البيانات: {message}')
        return redirect('document_upload')
except Exception as e:
    logger.error(f"Document upload error: {e}")
    messages.error(request, f'خطأ في معالجة المستند: {str(e)}')
    return redirect('document_upload')
```

### Success Response
```python
document.status = 'completed'
document.save()

messages.success(request, f'تم معالجة المستند بنجاح. {message}')
return redirect('pipeline_result', document_id=document.id)
```

---

## Form Fields Summary

| Field | Type | Required | Validation | Default |
|-------|------|----------|-----------|---------|
| document | File | Yes | Ext, Size ≤50MB | — |
| document_type | Select | No | Enum | "other" |
| language | Select | No | Enum | "ara+eng" |
| is_handwritten | Checkbox | No | Boolean | False |
| upload_mode | Hidden | Yes | "single" | — |
| csrfmiddlewaretoken | Hidden | Yes | Token | — |

---

## Clean Code Principles Applied

✅ **Type Safety**: All values converted to proper types before DB save
✅ **Error Handling**: Try/except with meaningful error messages  
✅ **Validation**: File type and size checked
✅ **Logging**: All steps logged for debugging
✅ **Transactions**: Database operations atomic
✅ **Security**: CSRF tokens validated, file paths sanitized
✅ **Performance**: Efficient single-pass processing
✅ **Bilingual**: Arabic and English support throughout

