from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet, ExtractedDataViewSet, TransactionViewSet,
    AccountViewSet, JournalEntryViewSet, ComplianceCheckViewSet, AuditFlagViewSet,
    InvoiceAuditReportViewSet
)
from .dashboard_views import (
    invoice_analysis_dashboard,
    invoice_detail,
    audit_report_detail,
    download_audit_report_pdf,
)

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'extracted-data', ExtractedDataViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'journal-entries', JournalEntryViewSet)
router.register(r'compliance-checks', ComplianceCheckViewSet)
router.register(r'audit-flags', AuditFlagViewSet)
router.register(r'audit-reports', InvoiceAuditReportViewSet, basename='audit-report')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', invoice_analysis_dashboard, name='invoice_analysis_dashboard'),
    path('invoice/<uuid:invoice_id>/', invoice_detail, name='invoice-detail'),
    path('audit-report/<uuid:report_id>/', audit_report_detail, name='audit-report-detail'),
    path('audit-report/<uuid:report_id>/pdf/', download_audit_report_pdf, name='audit-report-download-pdf'),
]
