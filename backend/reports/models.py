from django.db import models
from core.models import User, Organization
import uuid

class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('income_statement', 'Income Statement'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow'),
        ('vat_return', 'VAT Return'),
        ('audit_report', 'Audit Report'),
        ('custom', 'Custom'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('submitted', 'Submitted'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    report_name = models.CharField(max_length=255)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    data_json = models.JSONField(null=True, blank=True)
    storage_key = models.CharField(max_length=500, null=True, blank=True)
    storage_url = models.TextField(null=True, blank=True)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_reports')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reports')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reports'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['report_type']),
            models.Index(fields=['status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_name} - {self.status}"

class Insight(models.Model):
    INSIGHT_TYPE_CHOICES = [
        ('anomaly', 'Anomaly'),
        ('prediction', 'Prediction'),
        ('trend', 'Trend'),
        ('recommendation', 'Recommendation'),
        ('alert', 'Alert'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='insights')
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    description = models.TextField()
    related_entity_type = models.CharField(max_length=50, null=True, blank=True)
    related_entity_id = models.UUIDField(null=True, blank=True)
    data_json = models.JSONField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_insights')
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'insights'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['insight_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_resolved']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.severity}"
