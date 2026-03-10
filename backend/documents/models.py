from django.core.exceptions import ValidationError
from django.db import models
from core.models import User, Organization
import uuid

class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('bank_statement', 'Bank Statement'),
        ('ledger', 'Ledger'),
        ('contract', 'Contract'),
        ('purchase_order', 'Purchase Order'),
        ('expense_report', 'Expense Report'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('validated', 'Validated'),
        ('pending_review', 'Pending Review'),   # OCR unclear — awaiting human correction
    ]
    
    LANGUAGE_CHOICES = [
        ('ar', 'Arabic'),
        ('en', 'English'),
        ('mixed', 'Mixed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='documents')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField()  # in bytes
    storage_key = models.CharField(max_length=500)
    storage_url = models.TextField()
    content_hash = models.CharField(max_length=64, null=True, blank=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, null=True, blank=True)
    is_handwritten = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'documents'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['uploaded_by']),
        ]
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.file_name} - {self.status}"

class ExtractedData(models.Model):
    VALIDATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('validated', 'Validated'),
        ('rejected', 'Rejected'),
        ('corrected', 'Corrected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name='extracted_data')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='extracted_data')
    vendor_name = models.CharField(max_length=255, null=True, blank=True)
    vendor_tax_id = models.CharField(max_length=50, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_tax_id = models.CharField(max_length=50, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    raw_json = models.JSONField(null=True, blank=True)
    items_json = models.JSONField(null=True, blank=True)  # Line items
    raw_text_ar = models.TextField(null=True, blank=True)
    raw_text_en = models.TextField(null=True, blank=True)
    confidence = models.IntegerField(default=0)  # 0-100
    validation_status = models.CharField(max_length=20, choices=VALIDATION_STATUS_CHOICES, default='pending')
    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='validated_data')
    validated_at = models.DateTimeField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    
    # Phase 2: Normalization and Validation
    normalized_json = models.JSONField(null=True, blank=True)  # Normalized extracted data
    validation_errors = models.JSONField(null=True, blank=True)  # List of validation errors
    validation_warnings = models.JSONField(null=True, blank=True)  # List of validation warnings
    is_valid = models.BooleanField(default=False)  # Pass/fail validation
    validation_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Phase 3: Compliance Checks, Risk Scoring & Audit Summary
    compliance_checks = models.JSONField(null=True, blank=True)  # List of compliance check results
    risk_score = models.IntegerField(default=0)  # 0-100 numeric risk score
    risk_level = models.CharField(max_length=20, null=True, blank=True)  # Low, Medium, High, Critical
    audit_summary = models.JSONField(null=True, blank=True)  # executive_summary, key_risks, recommended_actions, final_status
    audit_completed_at = models.DateTimeField(null=True, blank=True)  # When Phase 3 completed
    
    extraction_status = models.CharField(max_length=20, default='pending')  # pending, extracted, failed, pending_review
    extraction_error = models.TextField(null=True, blank=True)  # Error message if extraction failed
    extraction_completed_at = models.DateTimeField(null=True, blank=True)  # When extraction completed

    # Extraction provenance — SOLID: open for extension (new providers) without modifying callers
    is_fallback = models.BooleanField(default=False)  # True when Tesseract was used instead of OpenAI
    extraction_provider = models.CharField(max_length=50, default='unknown')  # 'openai_vision' | 'tesseract_ocr'

    # Human correction fields (used when status = pending_review)
    review_notes = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_extractions'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Phase 4: Cross-Document Intelligence & Vendor Risk
    duplicate_score = models.IntegerField(default=0, null=True, blank=True)  # 0-100, potential duplicate score
    duplicate_matched_document = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='duplicate_matches')  # Reference to matched document
    anomaly_flags = models.JSONField(null=True, blank=True)  # Array of anomaly flags detected
    anomaly_score = models.IntegerField(default=0, null=True, blank=True)  # 0-100 anomaly score
    cross_document_findings_count = models.IntegerField(default=0)  # Count of cross-document findings
    vendor_risk_score = models.IntegerField(default=0, null=True, blank=True)  # 0-100 vendor risk score
    vendor_risk_level = models.CharField(max_length=20, null=True, blank=True)  # Low, Medium, High, Critical
    phase4_completed_at = models.DateTimeField(null=True, blank=True)  # When Phase 4 completed
    
    class Meta:
        db_table = 'extracted_data'
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['organization']),
            models.Index(fields=['validation_status']),
            models.Index(fields=['vendor_name']),
            models.Index(fields=['invoice_date']),
            models.Index(fields=['total_amount']),
        ]
    
    def __str__(self):
        return f"Extracted data for {self.document.file_name}"
    
    def get_risk_description(self):
        """Get Arabic/English description for risk level with explanation"""
        descriptions = {
            'low': {
                'ar': 'منخفضة - مستوى منخفض من المخاطر',
                'en': 'Low - Minimal risk detected',
                'icon': '✓',
                'color': 'success',
                'details_ar': 'الفاتورة تبدو صحيحة وموثوقة. لا توجد مشاكل جوهرية.',
                'details_en': 'Invoice appears valid with consistent data and no major issues.'
            },
            'medium': {
                'ar': 'متوسطة - مستوى متوسط من المخاطر',
                'en': 'Medium - Moderate risk detected',
                'icon': '⚠',
                'color': 'warning',
                'details_ar': 'هناك بعض المشاكل التي تحتاج إلى مراجعة إضافية قبل الموافقة.',
                'details_en': 'Some issues detected that require manual verification before approval.'
            },
            'high': {
                'ar': 'عالية - مستوى عالي من المخاطر',
                'en': 'High - Significant risk detected',
                'icon': '!',
                'color': 'danger',
                'details_ar': 'هناك عدة مشاكل تتطلب تدخل يدوي فوري للمراجعة والموافقة.',
                'details_en': 'Multiple issues detected. Manual intervention required before approval.'
            },
            'critical': {
                'ar': 'حرجة - مستوى حرج من المخاطر',
                'en': 'Critical - Severe risk detected',
                'icon': '✕',
                'color': 'dark',
                'details_ar': 'الفاتورة فيها مشاكل خطيرة جداً. يجب رفضها أو تصحيحها بشكل كامل.',
                'details_en': 'Critical issues detected. Invoice should be rejected or completely corrected.'
            },
        }
        return descriptions.get(self.risk_level, {
            'ar': 'غير معروف',
            'en': 'Unknown',
            'icon': '?',
            'color': 'secondary',
            'details_ar': 'لم يتم تحديد مستوى المخاطر',
            'details_en': 'Risk level not determined'
        })


class Vendor(models.Model):
    """Vendor master data scoped per tenant organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='vendors'
    )
    name = models.CharField(max_length=255)
    commercial_registration = models.CharField(max_length=100, null=True, blank=True)
    vat_number = models.CharField(max_length=20, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vendors'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vendors'
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'vat_number'],
                condition=models.Q(vat_number__isnull=False) & ~models.Q(vat_number=''),
                name='uniq_vendor_org_vat',
            ),
        ]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['vat_number']),
            models.Index(fields=['name']),
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.vat_number or 'no-vat'})"


class InvoiceRecord(models.Model):
    """Normalized invoice record used by the ingestion layer."""

    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invoice_records'
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='invoice_records'
    )
    extracted_data = models.OneToOneField(
        'ExtractedData',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_record'
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name='invoice_records'
    )
    customer_organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='customer_invoice_records'
    )
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_vat_number = models.CharField(max_length=20, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='SAR')
    subtotal_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=18, decimal_places=4, null=True, blank=True)
    cost_center = models.CharField(max_length=100, null=True, blank=True)
    accounting_account = models.ForeignKey(
        'Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_records'
    )
    budget = models.ForeignKey(
        'FinancialBudget',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice_records'
    )
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_invoice_records'
    )
    raw_json = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_invoice_records'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoice_records'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['vendor']),
            models.Index(fields=['invoice_number']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['total_amount']),
            models.Index(fields=['approval_status']),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and previous.approval_status == 'approved':
                immutable_fields = [
                    'document_id',
                    'vendor_id',
                    'customer_organization_id',
                    'customer_name',
                    'customer_vat_number',
                    'invoice_number',
                    'issue_date',
                    'due_date',
                    'currency',
                    'subtotal_amount',
                    'vat_amount',
                    'total_amount',
                    'cost_center',
                    'accounting_account_id',
                    'budget_id',
                    'raw_json',
                ]
                for field_name in immutable_fields:
                    if getattr(previous, field_name) != getattr(self, field_name):
                        raise ValidationError('Approved invoices cannot be modified.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number or 'draft'} - {self.vendor.name}"


class InvoiceLineItem(models.Model):
    """Normalized line item rows for future price and anomaly analysis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(
        InvoiceRecord,
        on_delete=models.CASCADE,
        related_name='line_items'
    )
    line_number = models.PositiveIntegerField(default=1)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    unit_price = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    line_total = models.DecimalField(max_digits=18, decimal_places=4, default=0)
    raw_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'invoice_line_items'
        constraints = [
            models.UniqueConstraint(
                fields=['invoice', 'line_number'],
                name='uniq_invoice_line_number',
            ),
        ]
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['description']),
        ]
        ordering = ['line_number']

    def save(self, *args, **kwargs):
        if self.invoice_id and self.invoice.approval_status == 'approved':
            if self.pk is None:
                raise ValidationError('Approved invoices cannot be modified.')
            previous = type(self).objects.filter(pk=self.pk).first()
            if previous and (
                previous.description != self.description
                or previous.quantity != self.quantity
                or previous.unit_price != self.unit_price
                or previous.line_total != self.line_total
            ):
                raise ValidationError('Approved invoices cannot be modified.')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice.invoice_number or self.invoice_id} #{self.line_number}"


class AuditSession(models.Model):
    """Tracks the ordered audit workflow for one document processing run."""

    SOURCE_CHOICES = [
        ('web_upload', 'Web Upload'),
        ('api_upload', 'API Upload'),
        ('background_task', 'Background Task'),
        ('ocr_signal', 'OCR Signal'),
        ('re_audit', 'Re-Audit'),
    ]

    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('published', 'Published'),
        ('failed', 'Failed'),
    ]

    STAGE_CHOICES = [
        ('upload_file', 'Upload File'),
        ('create_audit_session', 'Create AuditSession'),
        ('save_document', 'Save Document'),
        ('ai_extraction', 'AI Extraction'),
        ('normalization', 'Normalization'),
        ('validation', 'Validation'),
        ('compliance_engine', 'Compliance Engine'),
        ('risk_score', 'Risk Score'),
        ('findings', 'Findings'),
        ('ai_executive_summary', 'AI Executive Summary'),
        ('publish_to_dashboard', 'Publish to Dashboard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='audit_sessions',
    )
    started_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='started_audit_sessions',
    )
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default='web_upload')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    current_stage = models.CharField(max_length=40, choices=STAGE_CHOICES, default='create_audit_session')
    file_name = models.CharField(max_length=500, null=True, blank=True)
    content_hash = models.CharField(max_length=64, null=True, blank=True)
    document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_sessions',
    )
    extracted_data = models.ForeignKey(
        ExtractedData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_sessions',
    )
    invoice_record = models.ForeignKey(
        InvoiceRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_sessions',
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_sessions',
    )
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_tax_id = models.CharField(max_length=50, null=True, blank=True)
    stages_json = models.JSONField(default=dict, blank=True)
    dashboard_payload = models.JSONField(default=dict, blank=True)
    last_error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'audit_sessions'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['source']),
            models.Index(fields=['current_stage']),
            models.Index(fields=['document']),
        ]
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.file_name or self.id} - {self.status}"

class Account(models.Model):
    """Chart of Accounts - Double-entry bookkeeping support"""
    ACCOUNT_TYPE_CHOICES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]
    
    ACCOUNT_SUBTYPE_CHOICES = [
        # Assets
        ('cash', 'Cash & Cash Equivalents'),
        ('accounts_receivable', 'Accounts Receivable'),
        ('inventory', 'Inventory'),
        ('prepaid', 'Prepaid Expenses'),
        ('fixed_assets', 'Fixed Assets'),
        # Liabilities
        ('accounts_payable', 'Accounts Payable'),
        ('vat_payable', 'VAT Payable'),
        ('loans', 'Loans & Borrowings'),
        ('accrued', 'Accrued Liabilities'),
        # Equity
        ('capital', 'Capital'),
        ('retained_earnings', 'Retained Earnings'),
        # Revenue
        ('sales', 'Sales Revenue'),
        ('service_income', 'Service Income'),
        ('other_income', 'Other Income'),
        # Expenses
        ('cost_of_goods', 'Cost of Goods Sold'),
        ('salaries', 'Salaries & Wages'),
        ('rent', 'Rent Expense'),
        ('utilities', 'Utilities'),
        ('marketing', 'Marketing & Advertising'),
        ('other_expense', 'Other Expenses'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='accounts')
    account_code = models.CharField(max_length=20)
    account_name = models.CharField(max_length=255)
    account_name_ar = models.CharField(max_length=255, null=True, blank=True)  # Arabic name
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    account_subtype = models.CharField(max_length=30, choices=ACCOUNT_SUBTYPE_CHOICES, null=True, blank=True)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts')
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default='SAR')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accounts'
        unique_together = [['organization', 'account_code']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['account_type']),
            models.Index(fields=['account_code']),
        ]
        ordering = ['account_code']
    
    def __str__(self):
        return f"{self.account_code} - {self.account_name}"


class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='transactions')
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    category = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=10, default='SAR')
    description = models.TextField(null=True, blank=True)
    transaction_date = models.DateTimeField()
    account_code = models.CharField(max_length=50, null=True, blank=True)
    vendor_customer = models.CharField(max_length=255, null=True, blank=True)
    vat_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_reconciled = models.BooleanField(default=False)
    reconciled_at = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=100, null=True, blank=True)
    is_anomaly = models.BooleanField(default=False)
    anomaly_type = models.CharField(max_length=100, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['is_anomaly']),
        ]
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency}"


class JournalEntry(models.Model):
    """Double-entry bookkeeping journal entries"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('reversed', 'Reversed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='journal_entries')
    entry_number = models.CharField(max_length=50)
    entry_date = models.DateTimeField()
    description = models.TextField()
    reference = models.CharField(max_length=255, null=True, blank=True)
    document = models.ForeignKey(Document, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_balanced = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='journal_entries')
    posted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='posted_entries')
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'journal_entries'
        unique_together = [['organization', 'entry_number']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['entry_date']),
            models.Index(fields=['status']),
        ]
        ordering = ['-entry_date']
    
    def __str__(self):
        return f"{self.entry_number} - {self.description[:50]}"


class JournalEntryLine(models.Model):
    """Individual debit/credit lines in a journal entry"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_lines')
    description = models.CharField(max_length=500, null=True, blank=True)
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'journal_entry_lines'
        indexes = [
            models.Index(fields=['journal_entry']),
            models.Index(fields=['account']),
        ]
    
    def __str__(self):
        return f"{self.account.account_code}: Dr {self.debit_amount} Cr {self.credit_amount}"


class ComplianceCheck(models.Model):
    """Compliance checking and scoring"""
    CHECK_TYPE_CHOICES = [
        ('vat', 'VAT Compliance'),
        ('zatca', 'ZATCA Compliance'),
        ('shariah', 'Shariah Compliance'),
        ('ifrs', 'IFRS Compliance'),
        ('aml', 'Anti-Money Laundering'),
        ('general', 'General Compliance'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('warning', 'Warning'),
        ('exempted', 'Exempted'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='compliance_checks')
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES)
    check_name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    compliance_score = models.IntegerField(default=0)  # 0-100
    
    # Related entity (could be transaction, document, journal entry, etc.)
    related_entity_type = models.CharField(max_length=50, null=True, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    
    # Violation details
    violation_details = models.JSONField(null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_compliance')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    
    # Audit trail
    checked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='compliance_checks_performed')
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'compliance_checks'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['check_type']),
            models.Index(fields=['status']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.check_name} - {self.status}"


class AuditFlag(models.Model):
    """Audit flags for transactions requiring review"""
    FLAG_TYPE_CHOICES = [
        ('duplicate', 'Potential Duplicate'),
        ('unusual_amount', 'Unusual Amount'),
        ('unusual_timing', 'Unusual Timing'),
        ('missing_approval', 'Missing Approval'),
        ('vat_error', 'VAT Calculation Error'),
        ('compliance_violation', 'Compliance Violation'),
        ('fraud_risk', 'Potential Fraud'),
        ('data_quality', 'Data Quality Issue'),
        ('manual_review', 'Requires Manual Review'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_flags')
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_flags')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_flags')
    flag_type = models.CharField(max_length=30, choices=FLAG_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    description = models.TextField()
    details_json = models.JSONField(null=True, blank=True)
    
    # AI-detected vs manual
    is_ai_detected = models.BooleanField(default=True)
    confidence_score = models.IntegerField(default=0)  # 0-100 for AI detection
    
    # Resolution tracking
    is_resolved = models.BooleanField(default=False)
    resolution_action = models.CharField(max_length=50, null=True, blank=True)  # approved, rejected, corrected
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_flags')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_flags'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['flag_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.flag_type} - {self.title}"



class OCREvidence(models.Model):
    """
    OCR Evidence Record - سجل أدلة التعرف الضوئي
    
    AUDIT EVIDENCE: Stores OCR extraction results as immutable evidence.
    
    COMPLIANCE RULES:
    - OCR output is evidence, NOT source of truth
    - Original document is preserved separately
    - All extractions are timestamped and hashed
    - No editing of extracted text allowed
    """
    CONFIDENCE_LEVEL_CHOICES = [
        ('high', 'مرتفعة - High'),
        ('medium', 'متوسطة - Medium'),
        ('low', 'منخفضة - Low'),
        ('very_low', 'ضعيفة جداً - Very Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to original document
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE,
        related_name='ocr_evidence_records'
    )
    organization = models.ForeignKey(
        'core.Organization', on_delete=models.CASCADE,
        related_name='ocr_evidence'
    )
    
    # Extracted text (immutable)
    raw_text = models.TextField(
        help_text='Full extracted text - IMMUTABLE'
    )
    text_ar = models.TextField(
        null=True, blank=True,
        help_text='Arabic text portions'
    )
    text_en = models.TextField(
        null=True, blank=True,
        help_text='English text portions'
    )
    
    # OCR metadata
    confidence_score = models.IntegerField(
        default=0,
        help_text='OCR confidence 0-100'
    )
    confidence_level = models.CharField(
        max_length=20,
        choices=CONFIDENCE_LEVEL_CHOICES,
        default='low'
    )
    page_count = models.IntegerField(default=1)
    word_count = models.IntegerField(default=0)
    
    # Processing details
    ocr_engine = models.CharField(max_length=50, default='tesseract')
    ocr_version = models.CharField(max_length=50, null=True, blank=True)
    language_used = models.CharField(max_length=20, default='mixed')
    is_handwritten = models.BooleanField(default=False)
    processing_time_ms = models.IntegerField(default=0)
    
    # Structured data extraction (best-effort, not source of truth)
    extracted_invoice_number = models.CharField(max_length=100, null=True, blank=True)
    extracted_vat_number = models.CharField(max_length=20, null=True, blank=True)
    extracted_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    extracted_tax = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Invoice details extracted from OCR
    extracted_vendor_name = models.CharField(max_length=255, null=True, blank=True, help_text='Vendor/Supplier Name')
    extracted_vendor_address = models.TextField(null=True, blank=True, help_text='Vendor Address')
    extracted_customer_name = models.CharField(max_length=255, null=True, blank=True, help_text='Customer Name')
    extracted_customer_address = models.TextField(null=True, blank=True, help_text='Customer Address')
    extracted_invoice_date = models.DateField(null=True, blank=True, help_text='Invoice Date')
    extracted_due_date = models.DateField(null=True, blank=True, help_text='Due Date')
    extracted_currency = models.CharField(max_length=10, null=True, blank=True, default='SAR', help_text='Currency Code')
    extracted_items = models.JSONField(null=True, blank=True, help_text='Line items array')
    
    structured_data_json = models.JSONField(null=True, blank=True)
    
    # Evidence integrity
    evidence_hash = models.CharField(
        max_length=64,
        help_text='SHA-256 hash for evidence integrity'
    )
    
    # Audit trail
    extracted_by = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='ocr_extractions'
    )
    extracted_at = models.DateTimeField(auto_now_add=True)
    
    # Scope declaration
    scope_declaration = models.TextField(
        default='OCR EVIDENCE - READ-ONLY, NOT SOURCE OF TRUTH',
        help_text='Documents that this is audit evidence only'
    )
    
    class Meta:
        db_table = 'ocr_evidence'
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['organization']),
            models.Index(fields=['confidence_level']),
            models.Index(fields=['extracted_at']),
        ]
        ordering = ['-extracted_at']
    
    def __str__(self):
        return f"OCR Evidence: {self.document.file_name} ({self.confidence_level})"
    
    @classmethod
    def get_scope_documentation(cls):
        """Returns official scope documentation"""
        return {
            'system': 'FinAI Document OCR',
            'purpose': 'Audit Evidence Extraction',
            'scope_ar': '''
نطاق التعرف الضوئي - أدلة التدقيق فقط:

ما يقوم به النظام:
• استخراج النص من المستندات الممسوحة ضوئياً
• دعم اللغة العربية والإنجليزية
• التعرف على الخط اليدوي (أفضل جهد)
• تخزين النتائج كأدلة تدقيق

ما لا يقوم به النظام:
• لا يُعدّل النص المستخرج
• لا يُعتبر النص المستخرج مصدراً للحقيقة المحاسبية
• لا يُستخدم للقيود المحاسبية التلقائية
            ''',
            'scope_en': '''
OCR Scope - Audit Evidence Only:

What it DOES:
• Extract text from scanned documents
• Support Arabic and English languages
• Recognize handwriting (best-effort)
• Store results as audit evidence

What it does NOT do:
• Does NOT modify extracted text
• Extracted text is NOT source of accounting truth
• NOT used for automatic accounting entries
            ''',
            'disclaimer_ar': 'النص المستخرج هو دليل تدقيق فقط وليس مصدراً للحقيقة المحاسبية',
            'disclaimer_en': 'Extracted text is audit evidence only, not source of accounting truth',
        }


class InvoiceAuditFinding(models.Model):
    """
    Phase 2: Audit findings from invoice extraction validation
    
    Tracks discrepancies, VAT flags, and validation issues
    """
    FINDING_TYPE_CHOICES = [
        ('total_mismatch', 'Total Mismatch'),
        ('vat_flag', 'VAT Flag'),
        ('line_total_mismatch', 'Line Total Mismatch'),
        ('missing_field', 'Missing Field'),
        ('invalid_value', 'Invalid Value'),
        ('date_mismatch', 'Date Mismatch'),
        ('other', 'Other'),
    ]
    
    SEVERITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
        ('info', 'Info'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extracted_data = models.ForeignKey(
        ExtractedData,
        on_delete=models.CASCADE,
        related_name='audit_findings'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invoice_audit_findings'
    )
    
    finding_type = models.CharField(max_length=30, choices=FINDING_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    
    # Description
    description = models.TextField()
    field = models.CharField(max_length=100, null=True, blank=True)  # Field that triggered the finding
    
    # Numeric discrepancies
    expected_value = models.TextField(null=True, blank=True)  # Expected value for comparison
    actual_value = models.TextField(null=True, blank=True)    # Actual value found
    difference = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )  # Difference for numeric comparisons
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_invoice_findings'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoice_audit_findings'
        indexes = [
            models.Index(fields=['extracted_data']),
            models.Index(fields=['organization']),
            models.Index(fields=['finding_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-severity', '-created_at']
    
    def __str__(self):
        return f"Finding: {self.finding_type} ({self.severity}) on invoice {self.extracted_data.invoice_number}"


class AuditTrail(models.Model):
    """
    Phase 3: Comprehensive audit trail for invoice processing
    
    Tracks all events in the invoice lifecycle:
    - Upload
    - Extraction (Phase 1)
    - Normalization (Phase 2)
    - Validation (Phase 2)
    - Compliance checks (Phase 3)
    - Risk scoring (Phase 3)
    - Audit summary (Phase 3)
    - User review actions
    - Approval/rejection
    """
    
    EVENT_TYPE_CHOICES = [
        ('upload', 'Document Upload'),
        ('extraction', 'Invoice Extraction'),
        ('normalization', 'Data Normalization'),
        ('validation', 'Validation'),
        ('compliance_check', 'Compliance Check'),
        ('risk_score', 'Risk Scoring'),
        ('audit_summary', 'Audit Summary Generated'),
        ('review', 'User Review'),
        ('accept', 'Invoice Accepted'),
        ('reject', 'Invoice Rejected'),
        ('correct', 'Invoice Corrected'),
        ('finding_created', 'Audit Finding Created'),
        ('finding_resolved', 'Audit Finding Resolved'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extracted_data = models.ForeignKey(
        ExtractedData,
        on_delete=models.CASCADE,
        related_name='audit_trails'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='audit_trails'
    )
    
    # Event details
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')
    title = models.CharField(max_length=255)  # Event title (e.g., "Extraction completed successfully")
    description = models.TextField(null=True, blank=True)  # Event details
    
    # Timing information
    event_time = models.DateTimeField(auto_now_add=True)  # When event occurred
    duration_ms = models.IntegerField(null=True, blank=True)  # How long the operation took
    
    # User information
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_trail_events'
    )
    
    # Operation details (JSON for flexibility)
    details = models.JSONField(null=True, blank=True)  # operation-specific data
    
    # Result/status
    success = models.BooleanField(default=True)  # Did the operation succeed?
    result_summary = models.TextField(null=True, blank=True)  # Summary of result
    
    # Phase tracking
    phase = models.CharField(max_length=20, null=True, blank=True)  # 'phase1', 'phase2', 'phase3'
    
    class Meta:
        db_table = 'audit_trails'
        indexes = [
            models.Index(fields=['extracted_data']),
            models.Index(fields=['organization']),
            models.Index(fields=['event_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['event_time']),
            models.Index(fields=['success']),
        ]
        ordering = ['-event_time']
    
    def __str__(self):
        return f"{self.event_type} - {self.title} at {self.event_time}"

class CrossDocumentFinding(models.Model):
    """
    Phase 4: Cross-document findings for invoice anomalies
    
    Detects issues that require comparison across multiple invoices:
    - Potential duplicates
    - Unusual supplier amounts
    - Inconsistent tax behavior
    - Suspicious repeated discounts
    - Invoice frequency anomalies
    """
    
    FINDING_TYPE_CHOICES = [
        ('potential_duplicate', 'Potential Duplicate Invoice'),
        ('unusual_amount', 'Unusual Supplier Amount'),
        ('vat_inconsistency', 'VAT Inconsistency'),
        ('suspicious_discount', 'Suspicious Repeated Discount'),
        ('frequency_anomaly', 'Invoice Frequency Anomaly'),
        ('amount_spike', 'Unusual Amount Spike'),
        ('vendor_pattern_break', 'Breaks Vendor Pattern'),
        ('cross_vendor_match', 'Matches Another Vendor Invoice'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extracted_data = models.ForeignKey(
        ExtractedData,
        on_delete=models.CASCADE,
        related_name='cross_document_findings'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='cross_document_findings'
    )
    
    # Finding details
    finding_type = models.CharField(max_length=30, choices=FINDING_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Analysis details
    analysis_details = models.JSONField(null=True, blank=True)  # {
    #   "comparison_count": 5,
    #   "matching_invoices": [...],
    #   "anomaly_metrics": {...},
    #   "confidence_score": 85,
    # }
    
    # Referenced documents
    matched_document = models.ForeignKey(
        ExtractedData,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='matched_by_findings'
    )  # For duplicates/matches
    
    # Confidence/Score
    confidence_score = models.IntegerField(default=0)  # 0-100
    anomaly_score = models.IntegerField(default=0, null=True, blank=True)  # 0-100
    
    # Status
    is_resolved = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Open'),
            ('under_review', 'Under Review'),
            ('dismissed', 'Dismissed'),
            ('confirmed', 'Confirmed'),
            ('duplicate_confirmed', 'Duplicate Confirmed'),
        ],
        default='open'
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_cross_doc_findings'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(null=True, blank=True)
    
    # Audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cross_document_findings'
        indexes = [
            models.Index(fields=['extracted_data']),
            models.Index(fields=['organization']),
            models.Index(fields=['finding_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['status']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['matched_document']),
            models.Index(fields=['confidence_score']),
        ]
        ordering = ['-severity', '-confidence_score', '-created_at']
    
    def __str__(self):
        return f"{self.finding_type}: {self.title} ({self.severity})"


class VendorRisk(models.Model):
    """
    Phase 4: Vendor risk intelligence and history
    
    Tracks vendor-level metrics across all invoices:
    - Historical violations
    - Duplicate suspicion counts
    - Anomaly counts
    - Risk score and level
    """
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='vendor_risks'
    )
    vendor_name = models.CharField(max_length=255)
    vendor_tax_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Historical metrics
    total_invoices = models.IntegerField(default=0)
    duplicate_suspicion_count = models.IntegerField(default=0)
    anomaly_count = models.IntegerField(default=0)
    violation_count = models.IntegerField(default=0)
    compliance_failure_count = models.IntegerField(default=0)
    
    # Risk calculation
    risk_score = models.IntegerField(default=0)  # 0-100
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='low')
    
    # Analysis details
    risk_factors = models.JSONField(null=True, blank=True)  # {
    #   "duplicate_risk_pct": 5.2,
    #   "anomaly_rate": 10.3,
    #   "violation_rate": 2.1,
    #   "compliance_pass_rate": 87.5,
    #   "average_risk_score": 25,
    # }
    
    # Historical tags
    historical_issues = models.JSONField(null=True, blank=True)  # [
    #   {"type": "duplicate", "date": "2026-01-15"},
    #   {"type": "over_discount", "date": "2026-02-10"},
    # ]
    
    # Tracking
    last_analyzed_at = models.DateTimeField(null=True, blank=True)
    last_violation_at = models.DateTimeField(null=True, blank=True)
    last_anomaly_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendor_risks'
        unique_together = [['organization', 'vendor_name']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['vendor_name']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['risk_score']),
        ]
        ordering = ['-risk_score', '-anomaly_count']
    
    def __str__(self):
        return f"{self.vendor_name} ({self.risk_level})"


class AnomalyLog(models.Model):
    """
    Phase 4: Detailed anomaly detection log
    
    Tracks all anomalies detected per invoice for historical analysis and retraining
    """
    
    ANOMALY_TYPE_CHOICES = [
        ('amount_spike', 'Amount Spike'),
        ('amount_drop', 'Amount Drop'),
        ('discount_unusual', 'Unusual Discount'),
        ('frequency_spike', 'Frequency Spike'),
        ('frequency_drop', 'Frequency Drop'),
        ('pattern_break', 'Pattern Break'),
        ('tax_inconsistency', 'Tax Inconsistency'),
        ('date_anomaly', 'Date Anomaly'),
        ('duplicate_similarity', 'Duplicate Similarity'),
        ('vendor_new', 'New Vendor'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    extracted_data = models.ForeignKey(
        ExtractedData,
        on_delete=models.CASCADE,
        related_name='anomaly_logs'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='anomaly_logs'
    )
    
    # Anomaly details
    anomaly_type = models.CharField(max_length=30, choices=ANOMALY_TYPE_CHOICES)
    description = models.TextField()
    
    # Detected values
    detected_value = models.TextField(null=True, blank=True)  # The value that triggered anomaly
    expected_range = models.JSONField(null=True, blank=True)  # {min, max, mean, std_dev}
    deviation_percent = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Confidence and score
    confidence_score = models.IntegerField(default=0)  # 0-100
    severity = models.CharField(
        max_length=20,
        choices=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='warning'
    )
    
    # Historical context
    context_data = models.JSONField(null=True, blank=True)  # {
    #   "vendor_avg": 1000,
    #   "vendor_std_dev": 200,
    #   "last_invoice_amount": 950,
    #   "historical_count": 45,
    # }
    
    # Analysis method
    detection_method = models.CharField(
        max_length=50,
        choices=[
            ('statistical', 'Statistical Analysis'),
            ('pattern_matching', 'Pattern Matching'),
            ('rule_based', 'Rule-Based'),
            ('ml_model', 'ML Model'),
        ],
        default='statistical'
    )
    
    # Resolution
    is_confirmed = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'anomaly_logs'
        indexes = [
            models.Index(fields=['extracted_data']),
            models.Index(fields=['organization']),
            models.Index(fields=['anomaly_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['is_confirmed']),
        ]
        ordering = ['-severity', '-confidence_score', '-created_at']
    
    def __str__(self):
        return f"{self.anomaly_type} on {self.extracted_data.invoice_number}"


# ============================================================================
# PHASE 5: FINANCIAL INTELLIGENCE & FORECASTING MODELS
# ============================================================================

class CashFlowForecast(models.Model):
    """30/60/90 day cash flow projections by currency."""
    
    extracted_data = models.ForeignKey(ExtractedData, on_delete=models.CASCADE, related_name='cash_flow_forecasts')
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='cash_flow_forecasts')
    
    # Invoice payment terms
    invoice_date = models.DateField()
    due_date = models.DateField()
    invoice_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='SAR')
    
    # Forecast projections
    projected_payment_30d = models.DateField(null=True, blank=True)
    projected_payment_60d = models.DateField(null=True, blank=True)
    projected_payment_90d = models.DateField(null=True, blank=True)
    
    # Actual payment (if recorded)
    actual_payment_date = models.DateField(null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('scheduled', 'Scheduled'),
            ('paid', 'Paid'),
            ('overdue', 'Overdue'),
        ],
        default='pending'
    )
    
    # Forecast confidence
    confidence_score = models.FloatField(default=0.8)  # Based on vendor payment history
    forecast_method = models.CharField(
        max_length=50,
        choices=[
            ('historical_avg', 'Historical Average'),
            ('vendor_profile', 'Vendor Profile'),
            ('industry_standard', 'Industry Standard'),
            ('manual', 'Manual Entry'),
        ],
        default='historical_avg'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cash_flow_forecasts'
        indexes = [
            models.Index(fields=['organization', 'projected_payment_30d']),
            models.Index(fields=['organization', 'projected_payment_60d']),
            models.Index(fields=['organization', 'projected_payment_90d']),
            models.Index(fields=['currency']),
            models.Index(fields=['payment_status']),
        ]
        ordering = ['projected_payment_30d']
    
    def __str__(self):
        return f"CashFlow {self.currency} {self.invoice_amount} due {self.due_date}"


class SpendCategory(models.Model):
    """Monthly spending trends by category."""
    
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='spend_categories')
    
    # Category info
    category = models.CharField(max_length=100)
    month = models.DateField()  # First day of month for easy grouping
    
    # Spending metrics
    monthly_amount = models.DecimalField(max_digits=15, decimal_places=2)
    invoice_count = models.IntegerField(default=0)
    vendor_count = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default='SAR')
    
    # Trending
    previous_month_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    trend_percent = models.FloatField(default=0.0)  # Month-over-month growth %
    ytd_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Top vendors in category
    top_vendor = models.CharField(max_length=255, null=True, blank=True)
    top_vendor_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'spend_categories'
        indexes = [
            models.Index(fields=['organization', 'month']),
            models.Index(fields=['organization', 'category']),
            models.Index(fields=['month']),
        ]
        ordering = ['-month', '-monthly_amount']
        unique_together = ['organization', 'category', 'month']
    
    def __str__(self):
        return f"{self.category} {self.month.strftime('%B %Y')} - {self.currency} {self.monthly_amount}"


class VendorSpendMetrics(models.Model):
    """Vendor-level spending patterns and forecasts."""
    
    vendor_risk = models.OneToOneField(VendorRisk, on_delete=models.CASCADE, related_name='spend_metrics')
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='vendor_spend_metrics')
    
    # Spending summary
    total_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    invoice_count = models.IntegerField(default=0)
    average_invoice = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='SAR')
    
    # Monthly tracking
    current_month_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    previous_month_spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    ytd_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Growth analysis
    month_over_month_growth = models.FloatField(default=0.0)  # Percentage
    spending_velocity = models.CharField(
        max_length=20,
        choices=[
            ('stable', 'Stable'),
            ('growing', 'Growing'),
            ('declining', 'Declining'),
            ('volatile', 'Volatile'),
        ],
        default='stable'
    )
    anomaly_growth_rate = models.FloatField(default=0.0)  # % growth if anomalous
    
    # High-cost items
    highest_invoice_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    highest_invoice_date = models.DateField(null=True, blank=True)
    cost_concentration = models.FloatField(default=0.0)  # % of spend from top 5 invoices
    
    # Risk-based metrics
    is_critical_vendor = models.BooleanField(default=False)
    vendor_financial_health = models.CharField(
        max_length=20,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
            ('unknown', 'Unknown'),
        ],
        default='unknown'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vendor_spend_metrics'
        indexes = [
            models.Index(fields=['organization', '-total_spend']),
            models.Index(fields=['spending_velocity']),
            models.Index(fields=['is_critical_vendor']),
        ]
    
    def __str__(self):
        return f"{self.vendor_risk.vendor_name} - {self.currency} {self.total_spend}"


class FinancialBudget(models.Model):
    """Budget vs actual spend tracking."""
    
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='financial_budgets')
    
    # Budget scope
    category = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    currency = models.CharField(max_length=3, default='SAR')
    
    # Budget amounts
    budget_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    revised_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Utilization metrics
    utilization_percent = models.FloatField(default=0.0)
    variance_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    variance_percent = models.FloatField(default=0.0)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('on_track', 'On Track'),
            ('at_risk', 'At Risk'),
            ('overrun', 'Overrun'),
            ('underutilized', 'Underutilized'),
        ],
        default='on_track'
    )
    
    # Projection
    projected_final_spend = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    overrun_risk_percent = models.FloatField(default=0.0)
    
    # Approvals
    is_approved = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=255, null=True, blank=True)
    approval_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_budgets'
        indexes = [
            models.Index(fields=['organization', 'period_start']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.category} {self.period_start.year} - {self.status}"


class FinancialAlert(models.Model):
    """Intelligent financial alerts based on spending patterns and forecasts."""
    
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='financial_alerts')
    extracted_data = models.ForeignKey(ExtractedData, on_delete=models.SET_NULL, null=True, blank=True, related_name='financial_alerts')
    
    # Alert metadata
    alert_type = models.CharField(
        max_length=50,
        choices=[
            ('spend_spike', 'Spend Spike Detected'),
            ('duplicate_risk', 'Duplicate Invoice Risk'),
            ('anomaly_cluster', 'Anomaly Cluster Detected'),
            ('cash_flow_pressure', 'Cash Flow Pressure'),
            ('budget_overrun', 'Budget Overrun Risk'),
            ('vendor_risk_increase', 'Vendor Risk Increase'),
            ('payment_overdue', 'Payment Overdue'),
            ('category_variance', 'Category Variance'),
        ]
    )
    
    severity = models.CharField(
        max_length=10,
        choices=[
            ('critical', 'Critical'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium'
    )
    
    # Alert details
    title = models.CharField(max_length=255)
    description = models.TextField()
    trigger_details = models.JSONField(default=dict)  # Threshold values, actual values, etc.
    
    # Affected entities
    affected_vendor = models.CharField(max_length=255, null=True, blank=True)
    affected_category = models.CharField(max_length=100, null=True, blank=True)
    affected_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Actions
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=255, null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.CharField(max_length=255, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(null=True, blank=True)
    
    # Recommendations
    recommended_action = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # Alert expiration (e.g., 30 days)
    
    class Meta:
        db_table = 'financial_alerts'
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['severity']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['is_resolved']),
            models.Index(fields=['is_acknowledged']),
        ]
        ordering = ['-severity', '-created_at']
    
    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


class FinancialNarrative(models.Model):
    """AI-generated financial summaries and recommendations."""
    
    organization = models.ForeignKey('core.Organization', on_delete=models.CASCADE, related_name='financial_narratives')
    
    # Period information
    period_start = models.DateField()
    period_end = models.DateField()
    narrative_type = models.CharField(
        max_length=30,
        choices=[
            ('monthly', 'Monthly Summary'),
            ('quarterly', 'Quarterly Summary'),
            ('custom', 'Custom Period'),
        ],
        default='monthly'
    )
    
    # Narrative content
    narrative_text = models.TextField()  # Main AI-generated narrative
    executive_summary = models.TextField(null=True, blank=True)
    
    # Structured insights (JSON for flexibility)
    trends = models.JSONField(default=dict)  # Spending trends, growth rates, etc.
    risks = models.JSONField(default=dict)  # Identified risks and issues
    anomalies = models.JSONField(default=dict)  # Detected anomalies
    recommendations = models.JSONField(default=dict)  # Recommended actions
    
    # Metrics snapshot
    total_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    invoice_count = models.IntegerField(default=0)
    vendor_count = models.IntegerField(default=0)
    
    # Category breakdown
    top_categories = models.JSONField(default=dict)  # {category: amount}
    top_vendors = models.JSONField(default=dict)  # {vendor: amount}
    
    # Risk metrics
    overall_risk_score = models.FloatField(default=0.0)  # 0-100
    anomaly_count = models.IntegerField(default=0)
    duplicate_risk_count = models.IntegerField(default=0)
    
    # Generation method
    generation_method = models.CharField(
        max_length=50,
        choices=[
            ('openai', 'OpenAI GPT'),
            ('rule_based', 'Rule-Based'),
            ('hybrid', 'Hybrid'),
            ('manual', 'Manual Analysis'),
        ],
        default='hybrid'
    )
    
    # Quality metrics
    confidence_score = models.FloatField(default=0.8)
    data_completeness_percent = models.FloatField(default=100.0)
    
    # Status
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_to = models.CharField(max_length=255, null=True, blank=True)  # Email, dashboard, etc.
    
    # Versioning
    version = models.IntegerField(default=1)
    previous_narrative = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='next_version')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_narratives'
        indexes = [
            models.Index(fields=['organization', 'period_start']),
            models.Index(fields=['narrative_type']),
            models.Index(fields=['is_published']),
        ]
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.get_narrative_type_display()} {self.period_start.strftime('%B %Y')}"


class InvoiceAuditReport(models.Model):
    """
    Complete Financial Audit Report for Invoices
    
    Stores comprehensive audit findings including:
    - Document information
    - Invoice data extraction
    - Line items verification
    - Financial totals
    - Validation results
    - Compliance checks
    - Duplicate detection
    - Anomaly detection
    - Risk assessment
    - AI summary and recommendations
    - Audit trail
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('pending_review', 'Pending Review'),
    ]
    
    RECOMMENDATION_CHOICES = [
        ('approve', 'Approve'),
        ('manual_review', 'Manual Review Required'),
        ('reject', 'Reject'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to source data
    extracted_data = models.OneToOneField(
        ExtractedData,
        on_delete=models.CASCADE,
        related_name='audit_report'
    )
    document = models.OneToOneField(
        Document,
        on_delete=models.CASCADE,
        related_name='audit_report'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='invoice_audit_reports'
    )
    ocr_evidence = models.ForeignKey(
        OCREvidence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_reports'
    )
    
    # Report Metadata
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='generated'
    )
    report_number = models.CharField(
        max_length=20,
        help_text='Unique audit report identifier'
    )
    
    # =====================================================
    # 1. Document Information
    # =====================================================
    upload_date = models.DateTimeField(null=True, blank=True)
    ocr_engine = models.CharField(max_length=50, null=True, blank=True)
    ocr_confidence_score = models.IntegerField(default=0)  # 0-100
    processing_status = models.CharField(max_length=50, null=True, blank=True)
    
    # =====================================================
    # 2. Invoice Data Extraction
    # =====================================================
    extracted_invoice_number = models.CharField(max_length=100, null=True, blank=True)
    extracted_issue_date = models.DateField(null=True, blank=True)
    extracted_due_date = models.DateField(null=True, blank=True)
    extracted_vendor_name = models.CharField(max_length=255, null=True, blank=True)
    extracted_vendor_address = models.TextField(null=True, blank=True)
    extracted_vendor_tin = models.CharField(max_length=20, null=True, blank=True)  # Tax ID
    extracted_customer_name = models.CharField(max_length=255, null=True, blank=True)
    extracted_customer_address = models.TextField(null=True, blank=True)
    extracted_customer_tin = models.CharField(max_length=20, null=True, blank=True)  # Tax ID
    
    # =====================================================
    # 3. Line Items Details (stored as JSON)
    # =====================================================
    line_items_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of {product, description, quantity, unit_price, discount, total}'
    )
    
    # =====================================================
    # 4. Financial Totals
    # =====================================================
    subtotal_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    vat_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    currency = models.CharField(
        max_length=10,
        default='SAR',
        help_text='Currency code (SAR, USD, etc.)'
    )
    
    # =====================================================
    # 5. Validation Results
    # =====================================================
    validation_results_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Results for each validation check: {invoice_number: pass/warning/fail, vendor: ..., customer: ..., items: ..., total_match: ..., vat: ...}'
    )
    
    # =====================================================
    # 6. Compliance Checks
    # =====================================================
    compliance_checks_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of compliance findings'
    )
    
    # =====================================================
    # 7. Duplicate Detection
    # =====================================================
    duplicate_score = models.IntegerField(
        default=0,
        help_text='Duplicate probability 0-100'
    )
    duplicate_matched_documents_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of matched duplicate documents'
    )
    duplicate_status = models.CharField(
        max_length=50,
        choices=[
            ('no_duplicate', 'No Duplicate Detected'),
            ('low_risk', 'Low Duplicate Risk'),
            ('medium_risk', 'Medium Duplicate Risk'),
            ('high_risk', 'High Duplicate Risk'),
            ('confirmed_duplicate', 'Confirmed Duplicate'),
        ],
        default='no_duplicate'
    )
    
    # =====================================================
    # 8. Anomaly Detection
    # =====================================================
    anomaly_score = models.IntegerField(
        default=0,
        help_text='Anomaly probability 0-100'
    )
    anomaly_status = models.CharField(
        max_length=50,
        choices=[
            ('no_anomaly', 'No Anomaly Detected'),
            ('low_anomaly', 'Low Anomaly Risk'),
            ('medium_anomaly', 'Medium Anomaly Risk'),
            ('high_anomaly', 'High Anomaly Risk'),
            ('critical_anomaly', 'Critical Anomaly'),
        ],
        default='no_anomaly'
    )
    anomaly_explanation = models.TextField(
        null=True,
        blank=True,
        help_text='Description of detected anomalies'
    )
    anomaly_reasons_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of anomaly reasons'
    )
    
    # =====================================================
    # 9. Risk Assessment
    # =====================================================
    risk_score = models.IntegerField(
        default=0,
        help_text='Overall risk score 0-100'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='low'
    )
    risk_factors_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Array of identified risk factors'
    )
    
    # =====================================================
    # 10. AI Summary & Recommendations
    # =====================================================
    ai_summary = models.TextField(
        null=True,
        blank=True,
        help_text='AI-generated summary in English'
    )
    ai_summary_ar = models.TextField(
        null=True,
        blank=True,
        help_text='AI-generated summary in Arabic'
    )
    ai_findings = models.TextField(
        null=True,
        blank=True,
        help_text='AI analysis of problems and issues'
    )
    ai_findings_ar = models.TextField(
        null=True,
        blank=True,
        help_text='AI analysis in Arabic'
    )
    ai_review_required = models.BooleanField(
        default=False,
        help_text='Whether AI recommends manual review'
    )
    
    # =====================================================
    # 10. Recommendations
    # =====================================================
    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        default='manual_review'
    )
    recommendation_reason = models.TextField(
        null=True,
        blank=True,
        help_text='Reason for the recommendation'
    )
    recommendation_reason_ar = models.TextField(
        null=True,
        blank=True,
        help_text='Reason in Arabic'
    )
    
    # =====================================================
    # 11. Audit Trail
    # =====================================================
    audit_trail_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Timeline of all processing steps'
    )
    
    # Report Generation Details
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generated_audit_reports'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_audit_reports'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_audit_reports'
    )
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Full Report JSON (for fast retrieval and export)
    full_report_json = models.JSONField(
        null=True,
        blank=True,
        help_text='Complete report as JSON for export and storage'
    )
    
    class Meta:
        db_table = 'invoice_audit_reports'
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['extracted_data']),
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['generated_at']),
        ]
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Audit Report #{self.report_number} - {self.extracted_invoice_number} ({self.risk_level})"
