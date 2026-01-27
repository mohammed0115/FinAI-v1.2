from django.contrib import admin
from .models import (
    RegulatoryReference, ZATCAInvoice, ZATCAValidationResult,
    VATReconciliation, VATDiscrepancy, ZakatCalculation,
    ZakatDiscrepancy, AuditFinding
)


@admin.register(RegulatoryReference)
class RegulatoryReferenceAdmin(admin.ModelAdmin):
    list_display = ['regulator', 'article_number', 'title_ar', 'category', 'is_active']
    list_filter = ['regulator', 'category', 'is_active']
    search_fields = ['title_ar', 'title_en', 'article_number']


@admin.register(ZATCAInvoice)
class ZATCAInvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'organization', 'buyer_name', 'total_including_vat', 'status', 'issue_date']
    list_filter = ['status', 'invoice_type_code', 'organization']
    search_fields = ['invoice_number', 'buyer_name', 'seller_name']
    date_hierarchy = 'issue_date'


@admin.register(VATReconciliation)
class VATReconciliationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'period_start', 'period_end', 'net_vat_due', 'total_variance', 'compliance_score', 'status']
    list_filter = ['status', 'period_type', 'organization']
    date_hierarchy = 'period_start'


@admin.register(ZakatCalculation)
class ZakatCalculationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'fiscal_year_end', 'net_zakat_base', 'zakat_due', 'status']
    list_filter = ['status', 'organization']
    date_hierarchy = 'fiscal_year_end'


@admin.register(AuditFinding)
class AuditFindingAdmin(admin.ModelAdmin):
    list_display = ['finding_number', 'organization', 'title_ar', 'finding_type', 'risk_level', 'is_resolved']
    list_filter = ['finding_type', 'risk_level', 'is_resolved', 'organization']
    search_fields = ['title_ar', 'title_en', 'finding_number']
