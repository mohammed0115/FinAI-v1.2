"""
Hard Rules Audit Models - نماذج تدقيق القواعد الصارمة

Django models for logging all Hard Rules Engine evaluations.
"""
from django.db import models
from django.utils import timezone
import uuid


class HardRulesEvaluation(models.Model):
    """
    سجل تقييم القواعد الصارمة
    Log of Hard Rules Engine evaluations
    """
    STATUS_CHOICES = [
        ('PASS', 'ناجح - Pass'),
        ('FAIL', 'فشل - Fail'),
        ('BLOCKED', 'محظور - Blocked'),
        ('WARNING', 'تحذير - Warning'),
    ]
    
    EVALUATION_TYPE_CHOICES = [
        ('invoice', 'فاتورة - Invoice'),
        ('journal_entry', 'قيد يومية - Journal Entry'),
        ('transaction', 'معاملة - Transaction'),
        ('document', 'مستند - Document'),
        ('full_flow', 'تدفق كامل - Full Flow'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE, 
        related_name='hard_rules_evaluations',
        null=True, blank=True
    )
    user = models.ForeignKey(
        'core.User', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='hard_rules_evaluations'
    )
    
    # Evaluation metadata
    evaluation_type = models.CharField(max_length=20, choices=EVALUATION_TYPE_CHOICES)
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Results
    overall_status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    is_eligible_for_ai = models.BooleanField(default=False)
    
    # Counts
    total_rules_checked = models.IntegerField(default=0)
    passed_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    blocked_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    
    # Detailed results (JSON)
    results_json = models.JSONField(null=True, blank=True)
    critical_failures_json = models.JSONField(null=True, blank=True)
    blocking_issues_json = models.JSONField(null=True, blank=True)
    
    # Messages
    blocking_message = models.TextField(null=True, blank=True)
    blocking_message_ar = models.TextField(null=True, blank=True)
    
    # Integrity
    report_hash = models.CharField(max_length=64)
    
    # Timestamps
    evaluated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'hard_rules_evaluations'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['overall_status']),
            models.Index(fields=['evaluation_type']),
            models.Index(fields=['evaluated_at']),
            models.Index(fields=['entity_id']),
        ]
        ordering = ['-evaluated_at']
    
    def __str__(self):
        return f"HRE {self.evaluation_type}: {self.overall_status} ({self.evaluated_at})"


class HardRulesRuleResult(models.Model):
    """
    نتيجة قاعدة صارمة فردية
    Individual Hard Rule evaluation result
    """
    STATUS_CHOICES = [
        ('PASS', 'ناجح - Pass'),
        ('FAIL', 'فشل - Fail'),
        ('BLOCKED', 'محظور - Blocked'),
        ('WARNING', 'تحذير - Warning'),
    ]
    
    CATEGORY_CHOICES = [
        ('accounting', 'محاسبة - Accounting'),
        ('invoice', 'فاتورة - Invoice'),
        ('vat', 'ض.ق.م - VAT'),
        ('compliance', 'امتثال - Compliance'),
        ('ocr', 'تعرف ضوئي - OCR'),
        ('security', 'أمان - Security'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    evaluation = models.ForeignKey(
        HardRulesEvaluation, 
        on_delete=models.CASCADE, 
        related_name='rule_results'
    )
    
    # Rule identification
    rule_id = models.CharField(max_length=20)
    rule_name = models.CharField(max_length=100)
    rule_name_ar = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Result
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    message = models.TextField()
    message_ar = models.TextField()
    
    # Details (JSON)
    details_json = models.JSONField(null=True, blank=True)
    
    class Meta:
        db_table = 'hard_rules_rule_results'
        indexes = [
            models.Index(fields=['evaluation']),
            models.Index(fields=['rule_id']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.rule_id}: {self.status}"


class AIExecutionGateLog(models.Model):
    """
    سجل بوابة تنفيذ الذكاء الاصطناعي
    Log of AI execution gate decisions
    """
    DECISION_CHOICES = [
        ('ALLOWED', 'مسموح - Allowed'),
        ('BLOCKED', 'محظور - Blocked'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        'core.Organization', 
        on_delete=models.CASCADE, 
        related_name='ai_gate_logs',
        null=True, blank=True
    )
    user = models.ForeignKey(
        'core.User', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='ai_gate_logs'
    )
    
    # Gate decision
    decision = models.CharField(max_length=10, choices=DECISION_CHOICES)
    ai_function_name = models.CharField(max_length=100)
    
    # Related evaluation
    evaluation = models.ForeignKey(
        HardRulesEvaluation,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='gate_logs'
    )
    
    # Blocking reason (if blocked)
    blocking_reason = models.TextField(null=True, blank=True)
    blocking_reason_ar = models.TextField(null=True, blank=True)
    
    # Timestamps
    gate_checked_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'ai_execution_gate_logs'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['decision']),
            models.Index(fields=['gate_checked_at']),
        ]
        ordering = ['-gate_checked_at']
    
    def __str__(self):
        return f"AI Gate: {self.decision} - {self.ai_function_name}"
