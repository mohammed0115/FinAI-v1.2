from django.urls import path
from .social_auth_views import (
    google_login, google_callback,
    facebook_login, facebook_callback,
)
from .web_views import (
    # Auth
    login_view, logout_view,
    # Dashboard
    dashboard_view,
    # Compliance
    compliance_overview_view, zatca_verification_view,
    # Findings
    audit_findings_list_view, audit_finding_detail_view,
    generate_ai_explanation_view, review_ai_explanation_view,
    # Transactions
    transactions_view, transaction_detail_view,
    accounts_list_view, account_detail_view,
    # Documents
    documents_view, document_upload_view,
    ocr_evidence_list_view, ocr_evidence_detail_view,
    ai_audit_reports_view, invoice_audit_report_view,
    # Reports
    arabic_report_view, download_pdf_report_view,
    reports_list_view, analytics_dashboard_view, resolve_insight_view,
    # Settings
    toggle_language_view, organization_settings_view,
)
from .views.document_views import process_pending_documents, reprocess_with_ai_view, pipeline_result_view
from .monitoring_views import (
    monitoring_dashboard_view, processing_pipeline_view,
    ocr_metrics_view, compliance_report_view, risk_dashboard_view,
)

urlpatterns = [
    # Auth
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # Social Auth — Google
    path('auth/google/', google_login, name='google_login'),
    path('auth/google/callback/', google_callback, name='google_callback'),

    # Social Auth — Facebook
    path('auth/facebook/', facebook_login, name='facebook_login'),
    path('auth/facebook/callback/', facebook_callback, name='facebook_callback'),
    
    # Language Toggle
    path('toggle-language/', toggle_language_view, name='toggle_language'),
    
    # Dashboard
    path('', dashboard_view, name='dashboard'),
    
    # Compliance
    path('compliance/', compliance_overview_view, name='compliance_overview'),
    path('compliance/zatca-verify/', zatca_verification_view, name='zatca_verification'),
    
    # Audit Findings
    path('findings/', audit_findings_list_view, name='audit_findings_list'),
    path('findings/<uuid:finding_id>/', audit_finding_detail_view, name='audit_finding_detail'),
    path('findings/<uuid:finding_id>/generate-ai/', generate_ai_explanation_view, name='generate_ai_explanation'),
    path('ai-explanation/<uuid:log_id>/review/', review_ai_explanation_view, name='review_ai_explanation'),
    
    # Transactions
    path('transactions/', transactions_view, name='transactions'),
    path('transactions/<uuid:transaction_id>/', transaction_detail_view, name='transaction_detail'),
    
    # Accounts
    path('accounts/', accounts_list_view, name='accounts_list'),
    path('accounts/<uuid:account_id>/', account_detail_view, name='account_detail'),
    
    # Reports
    path('reports/', reports_list_view, name='reports_list'),
    path('report/arabic/', arabic_report_view, name='arabic_report'),
    path('report/pdf/', download_pdf_report_view, name='download_pdf_report'),
    
    # Document OCR
    path('documents/upload/', document_upload_view, name='document_upload'),
    path('documents/process-pending/', process_pending_documents, name='process_pending_documents'),
    path('ocr/', ocr_evidence_list_view, name='ocr_evidence_list'),
    path('ocr/<uuid:evidence_id>/', ocr_evidence_detail_view, name='ocr_evidence_detail'),
    path('ocr/<uuid:evidence_id>/reprocess/', reprocess_with_ai_view, name='reprocess_with_ai'),
    path('pipeline/<uuid:document_id>/', pipeline_result_view, name='pipeline_result'),
    path('reports/ai-audit/', ai_audit_reports_view, name='ai_audit_reports'),
    path('reports/audit/<uuid:extracted_data_id>/', invoice_audit_report_view, name='invoice_audit_report'),
    
    # Legacy views
    path('documents/', documents_view, name='documents'),
    path('analytics/', analytics_dashboard_view, name='analytics_dashboard'),
    path('insights/<uuid:insight_id>/resolve/', resolve_insight_view, name='resolve_insight'),
    
    # Organization Settings
    path('settings/organization/', organization_settings_view, name='organization_settings'),
    
    # Monitoring & Dashboards
    path('monitoring/', monitoring_dashboard_view, name='monitoring_dashboard'),
    path('monitoring/pipeline/', processing_pipeline_view, name='processing_pipeline'),
    path('monitoring/ocr-metrics/', ocr_metrics_view, name='ocr_metrics'),
    path('monitoring/compliance/', compliance_report_view, name='compliance_report'),
    path('monitoring/risk/', risk_dashboard_view, name='risk_dashboard'),
]
