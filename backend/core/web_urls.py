from django.urls import path

from .social_auth_views import facebook_callback, facebook_login, google_callback, google_login
from documents.dashboard_views import audit_report_detail, download_audit_report_pdf
from .views.auth_views import LandingPageView, LoginPageView, LogoutPageView, RegisterPageView
from .views.compliance_views import ComplianceOverviewPageView, ZATCAVerificationPageView
from .views.document_page_views import (
    DocumentUploadPageView,
    DocumentsListPageView,
    OCREvidenceDetailPageView,
    OCREvidenceListPageView,
    PendingReviewSubmitView,
    PipelineResultPageView,
    ProcessPendingDocumentsView,
    ReprocessWithAIView,
)
from .views.finding_views import (
    AuditFindingDetailPageView,
    AuditFindingsListPageView,
    GenerateAIExplanationView,
    ReviewAIExplanationView,
)
from .views.monitoring_page_views import (
    ComplianceReportPageView,
    MonitoringDashboardPageView,
    OCRMetricsPageView,
    ProcessingPipelinePageView,
    RiskDashboardPageView,
)
from .views.report_views import (
    AIAuditReportsPageView,
    AnalyticsDashboardPageView,
    ArabicReportPageView,
    DownloadPdfReportView,
    InvoiceAuditReportPageView,
    ReportsListPageView,
    ResolveInsightActionView,
)
from .views.settings_views import OrganizationSettingsPageView, ToggleLanguageView
from .views.transaction_views import AccountDetailPageView, AccountsListPageView, TransactionDetailPageView, TransactionsPageView
from .views.dashboard_views import DashboardPageView


urlpatterns = [
    path('', LandingPageView.as_view(), name='landing'),
    path('login/', LoginPageView.as_view(), name='login'),
    path('register/', RegisterPageView.as_view(), name='register'),
    path('logout/', LogoutPageView.as_view(), name='logout'),
    path('auth/google/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),
    path('auth/facebook/', facebook_login, name='facebook_login'),
    path('auth/facebook/callback/', facebook_callback, name='facebook_callback'),
    path('toggle-language/', ToggleLanguageView.as_view(), name='toggle_language'),
    path('dashboard/', DashboardPageView.as_view(), name='dashboard'),
    path('compliance/', ComplianceOverviewPageView.as_view(), name='compliance_overview'),
    path('compliance/zatca-verify/', ZATCAVerificationPageView.as_view(), name='zatca_verification'),
    path('findings/', AuditFindingsListPageView.as_view(), name='audit_findings_list'),
    path('findings/<uuid:finding_id>/', AuditFindingDetailPageView.as_view(), name='audit_finding_detail'),
    path('findings/<uuid:finding_id>/generate-ai/', GenerateAIExplanationView.as_view(), name='generate_ai_explanation'),
    path('ai-explanation/<uuid:log_id>/review/', ReviewAIExplanationView.as_view(), name='review_ai_explanation'),
    path('transactions/', TransactionsPageView.as_view(), name='transactions'),
    path('transactions/<uuid:transaction_id>/', TransactionDetailPageView.as_view(), name='transaction_detail'),
    path('accounts/', AccountsListPageView.as_view(), name='accounts_list'),
    path('accounts/<uuid:account_id>/', AccountDetailPageView.as_view(), name='account_detail'),
    path('reports/', ReportsListPageView.as_view(), name='reports_list'),
    path('report/arabic/', ArabicReportPageView.as_view(), name='arabic_report'),
    path('report/pdf/', DownloadPdfReportView.as_view(), name='download_pdf_report'),
    path('audit-report/<uuid:report_id>/', audit_report_detail, name='web_audit_report_detail'),
    path('audit-report/<uuid:report_id>/pdf/', download_audit_report_pdf, name='web_audit_report_download_pdf'),
    path('documents/upload/', DocumentUploadPageView.as_view(), name='document_upload'),
    path('documents/process-pending/', ProcessPendingDocumentsView.as_view(), name='process_pending_documents'),
    path('ocr/', OCREvidenceListPageView.as_view(), name='ocr_evidence_list'),
    path('ocr/<uuid:evidence_id>/', OCREvidenceDetailPageView.as_view(), name='ocr_evidence_detail'),
    path('ocr/<uuid:evidence_id>/reprocess/', ReprocessWithAIView.as_view(), name='reprocess_with_ai'),
    path('pipeline/<uuid:document_id>/', PipelineResultPageView.as_view(), name='pipeline_result'),
    path(
        'pipeline/<uuid:document_id>/pending-review-submit/',
        PendingReviewSubmitView.as_view(),
        name='pending_review_submit',
    ),
    path('reports/ai-audit/', AIAuditReportsPageView.as_view(), name='ai_audit_reports'),
    path('reports/audit/<uuid:extracted_data_id>/', InvoiceAuditReportPageView.as_view(), name='invoice_audit_report'),
    path('documents/', DocumentsListPageView.as_view(), name='documents'),
    path('analytics/', AnalyticsDashboardPageView.as_view(), name='analytics_dashboard'),
    path('insights/<uuid:insight_id>/resolve/', ResolveInsightActionView.as_view(), name='resolve_insight'),
    path('settings/organization/', OrganizationSettingsPageView.as_view(), name='organization_settings'),
    path('monitoring/', MonitoringDashboardPageView.as_view(), name='monitoring_dashboard'),
    path('monitoring/pipeline/', ProcessingPipelinePageView.as_view(), name='processing_pipeline'),
    path('monitoring/ocr-metrics/', OCRMetricsPageView.as_view(), name='ocr_metrics'),
    path('monitoring/compliance/', ComplianceReportPageView.as_view(), name='compliance_report'),
    path('monitoring/risk/', RiskDashboardPageView.as_view(), name='risk_dashboard'),
]
