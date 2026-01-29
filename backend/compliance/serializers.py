"""
Compliance Serializers - مسلسلات الامتثال
Arabic-first serialization for GCC regulatory compliance
"""
from rest_framework import serializers
from .models import (
    RegulatoryReference, ZATCAInvoice, ZATCAValidationResult,
    VATReconciliation, VATDiscrepancy, ZakatCalculation,
    ZakatDiscrepancy, AuditFinding
)


class RegulatoryReferenceSerializer(serializers.ModelSerializer):
    """المرجع التنظيمي"""
    regulator_display = serializers.CharField(source='get_regulator_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = RegulatoryReference
        fields = '__all__'
        read_only_fields = ['id']


class ZATCAValidationResultSerializer(serializers.ModelSerializer):
    """نتيجة التحقق من الفاتورة"""
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    
    class Meta:
        model = ZATCAValidationResult
        fields = '__all__'
        read_only_fields = ['id', 'checked_at']


class ZATCAInvoiceSerializer(serializers.ModelSerializer):
    """الفاتورة الإلكترونية"""
    validation_results = ZATCAValidationResultSerializer(many=True, read_only=True)
    invoice_type_display = serializers.CharField(source='get_invoice_type_code_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ZATCAInvoice
        fields = '__all__'
        read_only_fields = ['id', 'uuid', 'invoice_hash', 'qr_code', 'created_at', 'updated_at']


class ZATCAInvoiceListSerializer(serializers.ModelSerializer):
    """قائمة الفواتير الإلكترونية - Lightweight list view"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ZATCAInvoice
        fields = [
            'id', 'invoice_number', 'uuid', 'buyer_name', 
            'total_including_vat', 'status', 'status_display',
            'issue_date', 'created_at'
        ]


class VATDiscrepancySerializer(serializers.ModelSerializer):
    """تفاوت ضريبة القيمة المضافة"""
    discrepancy_type_display = serializers.CharField(source='get_discrepancy_type_display', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = VATDiscrepancy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'resolved_at']


class VATReconciliationSerializer(serializers.ModelSerializer):
    """تسوية ضريبة القيمة المضافة"""
    discrepancies = VATDiscrepancySerializer(many=True, read_only=True)
    period_type_display = serializers.CharField(source='get_period_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prepared_by_name = serializers.CharField(source='prepared_by.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = VATReconciliation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class VATReconciliationSummarySerializer(serializers.ModelSerializer):
    """ملخص تسوية ضريبة القيمة المضافة"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    discrepancy_count = serializers.SerializerMethodField()
    
    class Meta:
        model = VATReconciliation
        fields = [
            'id', 'period_start', 'period_end', 'total_output_vat',
            'total_input_vat', 'net_vat_due', 'total_variance',
            'compliance_score', 'status', 'status_display', 'discrepancy_count'
        ]
    
    def get_discrepancy_count(self, obj):
        return obj.discrepancies.filter(is_resolved=False).count()


class ZakatDiscrepancySerializer(serializers.ModelSerializer):
    """تفاوت الزكاة"""
    discrepancy_type_display = serializers.CharField(source='get_discrepancy_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = ZakatDiscrepancy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'resolved_at']


class ZakatCalculationSerializer(serializers.ModelSerializer):
    """حساب الزكاة"""
    discrepancies = ZakatDiscrepancySerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prepared_by_name = serializers.CharField(source='prepared_by.name', read_only=True)
    
    class Meta:
        model = ZakatCalculation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ZakatCalculationSummarySerializer(serializers.ModelSerializer):
    """ملخص حساب الزكاة"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ZakatCalculation
        fields = [
            'id', 'fiscal_year_start', 'fiscal_year_end',
            'net_zakat_base', 'zakat_due', 'zakat_tax_difference',
            'compliance_score', 'status', 'status_display'
        ]


class AuditFindingSerializer(serializers.ModelSerializer):
    """نتيجة التدقيق"""
    finding_type_display = serializers.CharField(source='get_finding_type_display', read_only=True)
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    identified_by_name = serializers.CharField(source='identified_by.name', read_only=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True, allow_null=True)
    regulatory_reference_detail = RegulatoryReferenceSerializer(source='regulatory_reference', read_only=True)
    
    class Meta:
        model = AuditFinding
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'resolved_at']


class AuditFindingListSerializer(serializers.ModelSerializer):
    """قائمة نتائج التدقيق"""
    risk_level_display = serializers.CharField(source='get_risk_level_display', read_only=True)
    
    class Meta:
        model = AuditFinding
        fields = [
            'id', 'finding_number', 'title_ar', 'finding_type',
            'risk_level', 'risk_level_display', 'financial_impact',
            'is_resolved', 'created_at'
        ]


# Arabic Report Serializers
class ArabicAuditReportSerializer(serializers.Serializer):
    """
    تقرير التدقيق باللغة العربية
    Arabic Audit Report Format for ZATCA / Internal Audit / Board
    """
    # Report metadata
    report_number = serializers.CharField()
    report_date = serializers.DateField()
    report_title_ar = serializers.CharField()
    
    # Organization
    organization_name = serializers.CharField()
    organization_tax_id = serializers.CharField()
    
    # Executive Summary
    executive_summary_ar = serializers.CharField()
    overall_compliance_score = serializers.IntegerField()
    risk_rating = serializers.CharField()
    
    # Findings summary
    total_findings = serializers.IntegerField()
    critical_findings = serializers.IntegerField()
    high_risk_findings = serializers.IntegerField()
    medium_risk_findings = serializers.IntegerField()
    low_risk_findings = serializers.IntegerField()
    
    # Financial impact
    total_financial_impact = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    # Detailed findings
    findings = AuditFindingSerializer(many=True)
    
    # Recommendations
    recommendations_ar = serializers.ListField(child=serializers.CharField())
    
    # Conclusion
    conclusion_ar = serializers.CharField()
    
    # Auditor information
    auditor_name = serializers.CharField()
    auditor_title = serializers.CharField()
    audit_date = serializers.DateField()
