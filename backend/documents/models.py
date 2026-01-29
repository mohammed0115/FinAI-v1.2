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
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    invoice_number = models.CharField(max_length=100, null=True, blank=True)
    invoice_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=10, null=True, blank=True)
    items_json = models.JSONField(null=True, blank=True)  # Line items
    raw_text_ar = models.TextField(null=True, blank=True)
    raw_text_en = models.TextField(null=True, blank=True)
    confidence = models.IntegerField(default=0)  # 0-100
    validation_status = models.CharField(max_length=20, choices=VALIDATION_STATUS_CHOICES, default='pending')
    validated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='validated_data')
    validated_at = models.DateTimeField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'extracted_data'
        indexes = [
            models.Index(fields=['document']),
            models.Index(fields=['organization']),
            models.Index(fields=['validation_status']),
        ]
    
    def __str__(self):
        return f"Extracted data for {self.document.file_name}"

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
