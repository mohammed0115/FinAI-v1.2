"""
ZATCA, VAT, and Zakat Compliance Models for Saudi Arabia
هذا الملف يحتوي على نماذج الامتثال لهيئة الزكاة والضريبة والجمارك
"""
from django.db import models
from django.utils import timezone
from core.models import User, Organization
from decimal import Decimal
import uuid
import hashlib
import json


class RegulatoryReference(models.Model):
    """
    المرجع التنظيمي - Regulatory Reference for GCC Compliance
    Links findings to specific regulatory articles/clauses
    """
    REGULATOR_CHOICES = [
        ('zatca', 'هيئة الزكاة والضريبة والجمارك - ZATCA'),
        ('fta', 'الهيئة الاتحادية للضرائب - FTA (UAE)'),
        ('nbr', 'الجهاز الوطني للإيرادات - NBR (Bahrain)'),
        ('gta', 'الهيئة العامة للضرائب - GTA (Qatar)'),
        ('mof_kw', 'وزارة المالية - MOF (Kuwait)'),
        ('tra', 'جهاز الضرائب - TRA (Oman)'),
        ('ifrs', 'المعايير الدولية للتقارير المالية - IFRS'),
        ('gaap', 'المبادئ المحاسبية المقبولة عموماً - GAAP'),
    ]
    
    CATEGORY_CHOICES = [
        ('vat', 'ضريبة القيمة المضافة - VAT'),
        ('zakat', 'الزكاة - Zakat'),
        ('einvoice', 'الفوترة الإلكترونية - E-Invoicing'),
        ('transfer_pricing', 'التسعير التحويلي - Transfer Pricing'),
        ('aml', 'مكافحة غسل الأموال - AML'),
        ('corporate_tax', 'ضريبة الشركات - Corporate Tax'),
        ('withholding', 'الضريبة المستقطعة - Withholding Tax'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    regulator = models.CharField(max_length=20, choices=REGULATOR_CHOICES)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    
    # Article/Clause identification
    article_number = models.CharField(max_length=50)  # e.g., "المادة 53" or "Article 53"
    clause_number = models.CharField(max_length=50, null=True, blank=True)
    
    # Bilingual content (Arabic primary)
    title_ar = models.CharField(max_length=500)  # Arabic title (primary)
    title_en = models.CharField(max_length=500, null=True, blank=True)  # English (optional)
    description_ar = models.TextField()  # Arabic description
    description_en = models.TextField(null=True, blank=True)
    
    # Penalty information
    penalty_description_ar = models.TextField(null=True, blank=True)
    penalty_amount_min = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    penalty_amount_max = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Metadata
    effective_date = models.DateField(null=True, blank=True)
    last_updated = models.DateField(null=True, blank=True)
    source_url = models.URLField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'regulatory_references'
        unique_together = [['regulator', 'article_number', 'clause_number']]
        indexes = [
            models.Index(fields=['regulator']),
            models.Index(fields=['category']),
        ]
        ordering = ['regulator', 'article_number']
    
    def __str__(self):
        return f"{self.regulator} - {self.article_number}: {self.title_ar}"


class ZATCAInvoice(models.Model):
    """
    نموذج الفاتورة الإلكترونية - ZATCA E-Invoice Model
    Phase 2 Fatoorah compliant structure
    """
    INVOICE_TYPE_CHOICES = [
        ('388', 'فاتورة ضريبية - Tax Invoice'),
        ('381', 'إشعار دائن - Credit Note'),
        ('383', 'إشعار مدين - Debit Note'),
    ]
    
    INVOICE_SUBTYPE_CHOICES = [
        ('0100000', 'فاتورة ضريبية قياسية - Standard Tax Invoice'),
        ('0200000', 'فاتورة ضريبية مبسطة - Simplified Tax Invoice'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة - Draft'),
        ('validated', 'تم التحقق - Validated'),
        ('reported', 'تم الإبلاغ - Reported to ZATCA'),
        ('cleared', 'تمت الموافقة - Cleared'),
        ('rejected', 'مرفوضة - Rejected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='zatca_invoices')
    
    # Invoice Identification (mandatory ZATCA fields)
    invoice_number = models.CharField(max_length=127)  # ICV - Invoice Counter Value
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)  # Invoice UUID
    invoice_type_code = models.CharField(max_length=3, choices=INVOICE_TYPE_CHOICES, default='388')
    invoice_subtype = models.CharField(max_length=7, choices=INVOICE_SUBTYPE_CHOICES, default='0100000')
    
    # Dates
    issue_date = models.DateField()
    issue_time = models.TimeField()
    supply_date = models.DateField(null=True, blank=True)  # Actual supply date
    
    # Seller Information (from Organization)
    seller_name = models.CharField(max_length=255)
    seller_vat_number = models.CharField(max_length=15)  # 15 digits for SA
    seller_address = models.TextField()
    seller_city = models.CharField(max_length=100)
    seller_postal_code = models.CharField(max_length=10, null=True, blank=True)
    seller_country = models.CharField(max_length=2, default='SA')
    
    # Buyer Information
    buyer_name = models.CharField(max_length=255)
    buyer_vat_number = models.CharField(max_length=15, null=True, blank=True)
    buyer_address = models.TextField(null=True, blank=True)
    buyer_city = models.CharField(max_length=100, null=True, blank=True)
    buyer_postal_code = models.CharField(max_length=10, null=True, blank=True)
    buyer_country = models.CharField(max_length=2, default='SA')
    
    # Amounts
    total_excluding_vat = models.DecimalField(max_digits=15, decimal_places=2)
    total_vat = models.DecimalField(max_digits=15, decimal_places=2)
    total_including_vat = models.DecimalField(max_digits=15, decimal_places=2)
    total_discount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Currency
    currency_code = models.CharField(max_length=3, default='SAR')
    
    # Line items stored as JSON
    line_items_json = models.JSONField()
    
    # ZATCA Compliance Fields
    previous_invoice_hash = models.CharField(max_length=64, null=True, blank=True)  # SHA-256 hash
    invoice_hash = models.CharField(max_length=64, null=True, blank=True)
    qr_code = models.TextField(null=True, blank=True)  # Base64 encoded QR
    xml_content = models.TextField(null=True, blank=True)  # Signed XML
    
    # Validation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    validation_errors = models.JSONField(null=True, blank=True)
    zatca_response = models.JSONField(null=True, blank=True)
    
    # Audit
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_invoices')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to source document
    source_document = models.ForeignKey(
        'documents.Document', on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='zatca_invoices'
    )
    
    class Meta:
        db_table = 'zatca_invoices'
        unique_together = [['organization', 'invoice_number']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['status']),
            models.Index(fields=['issue_date']),
            models.Index(fields=['seller_vat_number']),
        ]
        ordering = ['-issue_date', '-created_at']
    
    def calculate_hash(self):
        """Calculate invoice hash for chain integrity"""
        hash_input = f"{self.invoice_number}|{self.uuid}|{self.issue_date}|{self.total_including_vat}|{self.previous_invoice_hash or ''}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def __str__(self):
        return f"فاتورة {self.invoice_number} - {self.buyer_name}"


class ZATCAValidationResult(models.Model):
    """
    نتيجة التحقق من الفاتورة - ZATCA Validation Result
    Stores validation checks for each invoice
    """
    CHECK_TYPE_CHOICES = [
        ('mandatory_field', 'حقل إلزامي - Mandatory Field'),
        ('format', 'تنسيق - Format'),
        ('calculation', 'حساب - Calculation'),
        ('business_rule', 'قاعدة عمل - Business Rule'),
        ('xml_schema', 'مخطط XML - XML Schema'),
        ('signature', 'توقيع - Signature'),
        ('hash', 'تجزئة - Hash'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(ZATCAInvoice, on_delete=models.CASCADE, related_name='validation_results')
    
    check_type = models.CharField(max_length=30, choices=CHECK_TYPE_CHOICES)
    field_name = models.CharField(max_length=100)
    
    # Result
    is_valid = models.BooleanField(default=False)
    error_code = models.CharField(max_length=50, null=True, blank=True)  # ZATCA error code
    
    # Bilingual messages
    message_ar = models.TextField()
    message_en = models.TextField(null=True, blank=True)
    
    # Regulatory reference
    regulatory_reference = models.ForeignKey(
        RegulatoryReference, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='validation_results'
    )
    
    checked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'zatca_validation_results'
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['is_valid']),
        ]


class VATReconciliation(models.Model):
    """
    تسوية ضريبة القيمة المضافة - VAT Reconciliation
    Reconciles VAT collected vs VAT reported
    """
    PERIOD_TYPE_CHOICES = [
        ('monthly', 'شهري - Monthly'),
        ('quarterly', 'ربع سنوي - Quarterly'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'مسودة - Draft'),
        ('in_progress', 'قيد المراجعة - In Progress'),
        ('completed', 'مكتمل - Completed'),
        ('submitted', 'تم التقديم - Submitted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='vat_reconciliations')
    
    # Period
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPE_CHOICES, default='monthly')
    period_start = models.DateField()
    period_end = models.DateField()
    
    # Output VAT (Sales)
    output_vat_sales = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    output_vat_adjustments = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_output_vat = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Input VAT (Purchases)
    input_vat_purchases = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    input_vat_imports = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    input_vat_adjustments = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_input_vat = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Net VAT
    net_vat_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # VAT from accounting system (GL)
    gl_vat_payable_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    gl_vat_receivable_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Variance Analysis
    output_vat_variance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    input_vat_variance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_variance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    variance_explanation_ar = models.TextField(null=True, blank=True)
    variance_explanation_en = models.TextField(null=True, blank=True)
    
    # Compliance Score
    compliance_score = models.IntegerField(default=0)  # 0-100
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Audit
    prepared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prepared_vat_reconciliations')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_vat_reconciliations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'vat_reconciliations'
        unique_together = [['organization', 'period_start', 'period_end']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['period_start']),
            models.Index(fields=['status']),
        ]
        ordering = ['-period_start']
    
    def calculate_variance(self):
        """Calculate VAT variances"""
        self.total_output_vat = self.output_vat_sales + self.output_vat_adjustments
        self.total_input_vat = self.input_vat_purchases + self.input_vat_imports + self.input_vat_adjustments
        self.net_vat_due = self.total_output_vat - self.total_input_vat
        
        # Compare with GL
        expected_net = self.gl_vat_payable_balance - self.gl_vat_receivable_balance
        self.total_variance = self.net_vat_due - expected_net
        
        # Calculate compliance score based on variance
        if abs(self.total_variance) < Decimal('1'):
            self.compliance_score = 100
        elif abs(self.total_variance) < Decimal('100'):
            self.compliance_score = 90
        elif abs(self.total_variance) < Decimal('1000'):
            self.compliance_score = 70
        else:
            self.compliance_score = 50
    
    def __str__(self):
        return f"تسوية ض.ق.م {self.period_start} - {self.period_end}"


class VATDiscrepancy(models.Model):
    """
    تفاوت ضريبة القيمة المضافة - VAT Discrepancy
    Individual discrepancies found during reconciliation
    """
    DISCREPANCY_TYPE_CHOICES = [
        ('timing', 'توقيت - Timing Difference'),
        ('calculation', 'حساب - Calculation Error'),
        ('missing_invoice', 'فاتورة مفقودة - Missing Invoice'),
        ('duplicate', 'مكرر - Duplicate'),
        ('rate_error', 'خطأ في النسبة - Rate Error'),
        ('exemption', 'إعفاء - Exemption Issue'),
        ('classification', 'تصنيف - Classification Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reconciliation = models.ForeignKey(VATReconciliation, on_delete=models.CASCADE, related_name='discrepancies')
    
    discrepancy_type = models.CharField(max_length=30, choices=DISCREPANCY_TYPE_CHOICES)
    
    # Related transaction/invoice
    transaction = models.ForeignKey(
        'documents.Transaction', on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='vat_discrepancies'
    )
    invoice = models.ForeignKey(
        ZATCAInvoice, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='discrepancies'
    )
    
    # Amounts
    expected_vat = models.DecimalField(max_digits=15, decimal_places=2)
    actual_vat = models.DecimalField(max_digits=15, decimal_places=2)
    variance = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Explanation (bilingual)
    description_ar = models.TextField()
    description_en = models.TextField(null=True, blank=True)
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolution_ar = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Regulatory reference
    regulatory_reference = models.ForeignKey(
        RegulatoryReference, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vat_discrepancies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vat_discrepancies'
        indexes = [
            models.Index(fields=['reconciliation']),
            models.Index(fields=['discrepancy_type']),
            models.Index(fields=['is_resolved']),
        ]


class ZakatCalculation(models.Model):
    """
    حساب الزكاة - Zakat Calculation
    Annual Zakat calculation for Saudi organizations
    """
    STATUS_CHOICES = [
        ('draft', 'مسودة - Draft'),
        ('calculated', 'تم الحساب - Calculated'),
        ('reviewed', 'تمت المراجعة - Reviewed'),
        ('submitted', 'تم التقديم - Submitted'),
        ('assessed', 'تم التقييم - Assessed by ZATCA'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='zakat_calculations')
    
    # Fiscal Year
    fiscal_year_start = models.DateField()
    fiscal_year_end = models.DateField()
    
    # === ZAKAT BASE CALCULATION ===
    # إجمالي حقوق الملكية
    total_equity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # الالتزامات طويلة الأجل
    long_term_liabilities = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # المخصصات
    provisions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # صافي الربح المعدل
    adjusted_net_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # الوعاء الزكوي الإيجابي
    positive_zakat_base = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # === DEDUCTIONS ===
    # الأصول الثابتة
    fixed_assets = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # الاستثمارات طويلة الأجل
    long_term_investments = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # الخسائر المتراكمة
    accumulated_losses = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # إجمالي الحسومات
    total_deductions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # === ZAKAT CALCULATION ===
    # الوعاء الزكوي الصافي
    net_zakat_base = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # نسبة الزكاة (2.5%)
    zakat_rate = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal('0.025'))
    
    # مبلغ الزكاة المستحق
    zakat_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # === VS TAX COMPARISON ===
    # ضريبة الدخل المستحقة (للمقارنة)
    income_tax_due = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # الفرق بين الزكاة والضريبة
    zakat_tax_difference = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    difference_explanation_ar = models.TextField(null=True, blank=True)
    
    # === DETAILED BREAKDOWN (JSON) ===
    calculation_details = models.JSONField(null=True, blank=True)
    adjustments_json = models.JSONField(null=True, blank=True)
    
    # === COMPLIANCE ===
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    compliance_score = models.IntegerField(default=0)
    findings_ar = models.TextField(null=True, blank=True)  # Arabic audit findings
    
    # === AUDIT TRAIL ===
    prepared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prepared_zakat')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_zakat')
    override_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='override_zakat')
    override_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'zakat_calculations'
        unique_together = [['organization', 'fiscal_year_start', 'fiscal_year_end']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['fiscal_year_end']),
            models.Index(fields=['status']),
        ]
        ordering = ['-fiscal_year_end']
    
    def calculate_zakat(self):
        """حساب الزكاة - Calculate Zakat"""
        # Positive base
        self.positive_zakat_base = (
            self.total_equity + 
            self.long_term_liabilities + 
            self.provisions + 
            self.adjusted_net_profit
        )
        
        # Total deductions
        self.total_deductions = (
            self.fixed_assets + 
            self.long_term_investments + 
            self.accumulated_losses
        )
        
        # Net base
        self.net_zakat_base = max(self.positive_zakat_base - self.total_deductions, Decimal('0'))
        
        # Zakat due (2.5%)
        self.zakat_due = self.net_zakat_base * self.zakat_rate
        
        # Difference from tax
        self.zakat_tax_difference = self.zakat_due - self.income_tax_due
    
    def __str__(self):
        return f"زكاة {self.organization.name} - {self.fiscal_year_end.year}"


class ZakatDiscrepancy(models.Model):
    """
    تفاوت الزكاة - Zakat Discrepancy
    Discrepancies between calculated and reported Zakat
    """
    DISCREPANCY_TYPE_CHOICES = [
        ('equity_classification', 'تصنيف حقوق الملكية - Equity Classification'),
        ('asset_valuation', 'تقييم الأصول - Asset Valuation'),
        ('provision_treatment', 'معالجة المخصصات - Provision Treatment'),
        ('profit_adjustment', 'تعديل الأرباح - Profit Adjustment'),
        ('deduction_eligibility', 'أهلية الحسومات - Deduction Eligibility'),
        ('calculation_error', 'خطأ حسابي - Calculation Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zakat_calculation = models.ForeignKey(ZakatCalculation, on_delete=models.CASCADE, related_name='discrepancies')
    
    discrepancy_type = models.CharField(max_length=30, choices=DISCREPANCY_TYPE_CHOICES)
    
    # Field affected
    field_name = models.CharField(max_length=100)
    
    # Amounts
    reported_amount = models.DecimalField(max_digits=15, decimal_places=2)
    calculated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    variance = models.DecimalField(max_digits=15, decimal_places=2)
    impact_on_zakat = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Explanation (Arabic primary)
    description_ar = models.TextField()
    description_en = models.TextField(null=True, blank=True)
    
    # Risk level
    RISK_LEVEL_CHOICES = [
        ('low', 'منخفض - Low'),
        ('medium', 'متوسط - Medium'),
        ('high', 'مرتفع - High'),
        ('critical', 'حرج - Critical'),
    ]
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='medium')
    
    # Resolution
    is_resolved = models.BooleanField(default=False)
    resolution_ar = models.TextField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Regulatory reference
    regulatory_reference = models.ForeignKey(
        RegulatoryReference, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='zakat_discrepancies'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'zakat_discrepancies'
        indexes = [
            models.Index(fields=['zakat_calculation']),
            models.Index(fields=['discrepancy_type']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['is_resolved']),
        ]


class AuditFinding(models.Model):
    """
    نتيجة التدقيق - Audit Finding
    Links findings to regulatory references with Arabic explanations
    """
    FINDING_TYPE_CHOICES = [
        ('compliance', 'امتثال - Compliance'),
        ('accuracy', 'دقة - Accuracy'),
        ('completeness', 'اكتمال - Completeness'),
        ('timeliness', 'التوقيت - Timeliness'),
        ('documentation', 'توثيق - Documentation'),
        ('internal_control', 'رقابة داخلية - Internal Control'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'منخفض - Low'),
        ('medium', 'متوسط - Medium'),
        ('high', 'مرتفع - High'),
        ('critical', 'حرج - Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_findings')
    
    # Finding identification
    finding_number = models.CharField(max_length=50)
    finding_type = models.CharField(max_length=30, choices=FINDING_TYPE_CHOICES)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES)
    
    # Bilingual content (Arabic primary)
    title_ar = models.CharField(max_length=500)
    title_en = models.CharField(max_length=500, null=True, blank=True)
    
    description_ar = models.TextField()  # Detailed finding in Arabic
    description_en = models.TextField(null=True, blank=True)
    
    # Impact
    impact_ar = models.TextField()  # Impact description in Arabic
    impact_en = models.TextField(null=True, blank=True)
    financial_impact = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Recommendation
    recommendation_ar = models.TextField()
    recommendation_en = models.TextField(null=True, blank=True)
    
    # Regulatory mapping
    regulatory_reference = models.ForeignKey(
        RegulatoryReference, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_findings'
    )
    
    # Related entities
    related_entity_type = models.CharField(max_length=50, null=True, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    
    # AI Explanation
    ai_explanation_ar = models.TextField(null=True, blank=True)  # Why AI flagged this
    ai_confidence = models.IntegerField(default=0)
    
    # Status
    is_resolved = models.BooleanField(default=False)
    management_response_ar = models.TextField(null=True, blank=True)
    action_plan_ar = models.TextField(null=True, blank=True)
    target_resolution_date = models.DateField(null=True, blank=True)
    
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_findings')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Audit trail
    identified_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='identified_findings')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'audit_findings'
        unique_together = [['organization', 'finding_number']]
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['finding_type']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.finding_number}: {self.title_ar}"



class ZATCALiveVerificationReport(models.Model):
    """
    تقرير التحقق المباشر من ZATCA - ZATCA Live Verification Report
    
    AUDIT EVIDENCE STORAGE
    
    This model stores verification results as audit evidence.
    FinAI performs READ-ONLY verification of existing invoice data.
    
    SCOPE LIMITATION:
    - Does NOT generate invoices
    - Does NOT submit to ZATCA
    - Does NOT sign invoices
    - Does NOT modify data
    
    WHAT IT DOES:
    - Stores verification results
    - Captures error codes and Arabic messages
    - Links to regulatory references
    - Provides audit trail
    """
    VERIFICATION_STATUS_CHOICES = [
        ('passed', 'ناجح - Passed'),
        ('warning', 'تحذير - Warning'),
        ('failed', 'فشل - Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to invoice being verified
    invoice = models.ForeignKey(
        ZATCAInvoice, on_delete=models.CASCADE, 
        related_name='live_verification_reports'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='zatca_verification_reports'
    )
    
    # Verification metadata
    verification_timestamp = models.DateTimeField()
    verification_type = models.CharField(
        max_length=50, 
        default='post_transaction',
        help_text='READ-ONLY verification type'
    )
    
    # Overall results
    overall_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES)
    compliance_score = models.IntegerField(default=0)  # 0-100
    
    # Check counts
    total_checks = models.IntegerField(default=0)
    passed_checks = models.IntegerField(default=0)
    failed_checks = models.IntegerField(default=0)
    warning_checks = models.IntegerField(default=0)
    
    # Detailed results (JSON)
    verification_results_json = models.JSONField(
        help_text='Detailed verification results'
    )
    hash_verification_json = models.JSONField(
        null=True, blank=True,
        help_text='Hash chain verification details'
    )
    
    # Summaries (Arabic primary)
    summary_ar = models.TextField(help_text='Arabic summary')
    summary_en = models.TextField(null=True, blank=True, help_text='English summary')
    
    # Error tracking
    critical_errors_json = models.JSONField(
        null=True, blank=True,
        help_text='Critical errors that block compliance'
    )
    
    # Audit trail
    verified_by = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='zatca_verifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Scope documentation
    scope_declaration = models.TextField(
        default='READ-ONLY POST-TRANSACTION VERIFICATION',
        help_text='Documents that this is read-only verification, not invoice submission'
    )
    
    class Meta:
        db_table = 'zatca_live_verification_reports'
        indexes = [
            models.Index(fields=['invoice']),
            models.Index(fields=['organization']),
            models.Index(fields=['overall_status']),
            models.Index(fields=['verification_timestamp']),
        ]
        ordering = ['-verification_timestamp']
    
    def __str__(self):
        return f"تحقق {self.invoice.invoice_number} - {self.overall_status} ({self.compliance_score}%)"
    
    @classmethod
    def get_scope_documentation(cls):
        """
        Returns official scope documentation for regulatory purposes
        """
        return {
            'system_name': 'FinAI - AI-Powered Financial Audit Platform',
            'service_type': 'READ-ONLY VERIFICATION',
            'scope_ar': '''
نطاق النظام - التحقق للقراءة فقط:

ما يقوم به النظام:
• التحقق من صحة بيانات الفواتير الموجودة مقابل متطلبات هيئة الزكاة والضريبة والجمارك
• التحقق من تنسيق الرقم الضريبي
• التحقق من صحة المعرف الفريد (UUID)
• التحقق من سلامة سلسلة التجزئة
• تسجيل نتائج التحقق كدليل تدقيق

ما لا يقوم به النظام:
• لا يُصدر فواتير
• لا يُرسل فواتير إلى هيئة الزكاة والضريبة والجمارك
• لا يوقّع الفواتير
• لا يُعدّل بيانات الفواتير
• لا يتصرف نيابة عن المكلفين
            ''',
            'scope_en': '''
System Scope - READ-ONLY VERIFICATION:

What the system DOES:
• Validates existing invoice data against ZATCA requirements
• Verifies VAT number format
• Checks UUID correctness
• Verifies hash chain integrity
• Stores verification results as audit evidence

What the system does NOT do:
• Does NOT generate invoices
• Does NOT submit invoices to ZATCA
• Does NOT sign invoices
• Does NOT modify invoice data
• Does NOT act on behalf of taxpayers
            ''',
            'regulatory_disclaimer_ar': 'هذا النظام هو نظام تدقيق ومراجعة فقط وليس نظام فوترة إلكترونية',
            'regulatory_disclaimer_en': 'This is an audit and review system only, not an e-invoicing system',
        }



class AIExplanationLog(models.Model):
    """
    سجل الشروحات الذكية - AI Explanation Audit Log
    
    AUDIT TRAIL for all AI-generated explanations.
    Maintains full traceability for compliance.
    
    IMPORTANT:
    - All explanations are ADVISORY ONLY
    - Human review is REQUIRED before any action
    - No automatic decisions based on this output
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to finding
    finding = models.ForeignKey(
        AuditFinding, on_delete=models.CASCADE,
        related_name='ai_explanation_logs'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='ai_explanation_logs'
    )
    
    # LLM Output
    explanation_ar = models.TextField(help_text='Generated Arabic explanation')
    confidence_score = models.IntegerField(default=0)
    confidence_level = models.CharField(max_length=20, default='medium')
    
    # Model metadata
    model_used = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    session_id = models.CharField(max_length=100)
    processing_time_ms = models.IntegerField(default=0)
    
    # Audit integrity
    audit_hash = models.CharField(max_length=64, help_text='SHA-256 hash for integrity')
    
    # Compliance flags
    is_advisory = models.BooleanField(default=True)
    requires_human_review = models.BooleanField(default=True)
    human_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_ai_explanations'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
    
    # Approval status
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'قيد المراجعة - Pending Review'),
        ('approved', 'معتمد - Approved'),
        ('modified', 'معدل - Modified'),
        ('rejected', 'مرفوض - Rejected'),
    ]
    approval_status = models.CharField(
        max_length=20, 
        choices=APPROVAL_STATUS_CHOICES,
        default='pending'
    )
    
    # Audit trail
    generated_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='generated_ai_explanations'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    
    # Scope declaration
    scope_declaration = models.TextField(
        default='ADVISORY ONLY - REQUIRES HUMAN REVIEW',
        help_text='Documents that this is advisory output requiring human review'
    )
    
    class Meta:
        db_table = 'ai_explanation_logs'
        indexes = [
            models.Index(fields=['finding']),
            models.Index(fields=['organization']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['generated_at']),
        ]
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"AI Explanation: {self.finding.finding_number} ({self.approval_status})"



class ZATCAVerificationLog(models.Model):
    """
    سجل التحقق من ZATCA API - ZATCA API Verification Log
    
    Standalone audit log for ZATCA verification requests.
    Does NOT require an existing invoice record.
    
    SCOPE: VERIFICATION ONLY
    - No invoice submission
    - No clearance or signing
    - Maintains auditor independence
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE,
        related_name='zatca_verification_logs'
    )
    
    # Verification details
    verification_type = models.CharField(max_length=50)  # vat_number, invoice_structure
    input_identifier = models.CharField(max_length=255)  # VAT number or Invoice UUID
    
    # Results
    is_valid = models.BooleanField(default=False)
    compliance_score = models.IntegerField(default=0)
    passed_checks = models.IntegerField(default=0)
    failed_checks = models.IntegerField(default=0)
    
    # Messages
    message_ar = models.TextField(null=True, blank=True)
    message_en = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    
    # Full response
    response_json = models.JSONField()
    
    # Processing
    processing_time_ms = models.IntegerField(default=0)
    audit_hash = models.CharField(max_length=64)
    
    # Audit trail
    verified_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='zatca_api_verifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Scope declaration
    scope_declaration = models.TextField(
        default='VERIFICATION ONLY - No submission, clearance, or signing',
        help_text='Documents the read-only nature of this verification'
    )
    
    class Meta:
        db_table = 'zatca_verification_logs'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['verification_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"ZATCA Verification: {self.verification_type} ({self.input_identifier[:20]})"

