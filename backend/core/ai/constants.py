"""
AI Service Constants and Configuration
"""
import os
from decimal import Decimal

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
OPENAI_VISION_MODEL = os.environ.get('OPENAI_VISION_MODEL', 'gpt-4o-mini')
OPENAI_TIMEOUT = int(os.environ.get('OPENAI_TIMEOUT', '120'))
OPENAI_MAX_TOKENS = int(os.environ.get('OPENAI_MAX_TOKENS', '2000'))
OPENAI_TEMPERATURE = float(os.environ.get('OPENAI_TEMPERATURE', '0.3'))

# File Processing Constraints
MAX_UPLOAD_SIZE_MB = int(os.environ.get('MAX_UPLOAD_SIZE', '50'))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
MAX_OCR_PAGES = int(os.environ.get('MAX_OCR_PAGES', '20'))
ALLOWED_DOCUMENT_TYPES = ['pdf', 'jpeg', 'png', 'jpg']

# AI Rate Limiting
AI_RATE_LIMIT_REQUESTS = int(os.environ.get('AI_RATE_LIMIT_REQUESTS', '100'))
AI_RATE_LIMIT_PERIOD = int(os.environ.get('AI_RATE_LIMIT_PERIOD', '3600'))  # seconds

# Retry Configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1  # seconds
MAX_RETRY_DELAY = 30  # seconds
EXPONENTIAL_BASE = 2

# OCR Configuration
OCR_MIN_CONFIDENCE = 0.6
TESSERACT_TIMEOUT = 60  # seconds
VISION_API_TIMEOUT = 120  # seconds

# Languages
SUPPORTED_LANGUAGES = ['ar', 'en']
DEFAULT_LANGUAGE = 'ar'

# Error Messages (English)
ERRORS_EN = {
    'file_not_found': 'File not found: {file_path}',
    'file_too_large': f'File size exceeds maximum of {MAX_UPLOAD_SIZE_MB}MB',
    'unsupported_type': 'Unsupported file type: {file_type}. Supported: {allowed}',
    'invalid_pdf': 'Invalid PDF file or corrupted',
    'ocr_failed': 'OCR processing failed: {error}',
    'api_error': 'OpenAI API error: {error}',
    'rate_limit': 'Rate limit exceeded. Please try again in {retry_after} seconds',
    'timeout': 'Operation timed out after {timeout}s',
    'invalid_json': 'Invalid JSON in API response',
    'invalid_organization': 'Organization not found or access denied',
}

# Error Messages (Arabic)
ERRORS_AR = {
    'file_not_found': 'لم يتم العثور على الملف: {file_path}',
    'file_too_large': f'حجم الملف يتجاوز الحد الأقصى من {MAX_UPLOAD_SIZE_MB}MB',
    'unsupported_type': 'نوع الملف غير مدعوم: {file_type}. الأنواع المدعومة: {allowed}',
    'invalid_pdf': 'ملف PDF غير صحيح أو تالف',
    'ocr_failed': 'فشل معالجة التعرف الضوئي: {error}',
    'api_error': 'خطأ في API الخاص بـ OpenAI: {error}',
    'rate_limit': 'تم تجاوز حد المعدل. يرجى المحاولة مرة أخرى في {retry_after} ثانية',
    'timeout': 'انتهت المهلة الزمنية بعد {timeout}ث',
    'invalid_json': 'JSON غير صحيح في استجابة API',
    'invalid_organization': 'المنظمة غير موجودة أو تم رفض الوصول',
}

# Confidence Levels
CONFIDENCE_HIGH = 0.8
CONFIDENCE_MEDIUM = 0.6
CONFIDENCE_LOW = 0.4

# Invoice Extraction Schema
INVOICE_EXTRACTION_SCHEMA = {
    'type': 'object',
    'properties': {
        'vendor_name': {'type': 'string'},
        'vendor_vat_number': {'type': 'string'},
        'invoice_number': {'type': 'string'},
        'invoice_date': {'type': 'string', 'format': 'date'},
        'due_date': {'type': 'string', 'format': 'date'},
        'customer_name': {'type': 'string'},
        'line_items': {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'description': {'type': 'string'},
                    'quantity': {'type': 'number'},
                    'unit_price': {'type': 'number'},
                    'tax_rate': {'type': 'number'},
                    'line_total': {'type': 'number'},
                },
                'required': ['description', 'quantity', 'unit_price']
            }
        },
        'subtotal': {'type': 'number'},
        'tax_amount': {'type': 'number'},
        'total': {'type': 'number'},
        'currency': {'type': 'string'},
        'payment_method': {'type': 'string'},
        'notes': {'type': 'string'},
    },
    'required': ['vendor_name', 'invoice_number', 'invoice_date', 'total', 'currency']
}
