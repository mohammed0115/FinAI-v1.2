from django.urls import path
from .views import (
    # Auth
    login_view, logout_view, register_view,
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
    documents_view, document_upload_view, process_pending_documents,
    ocr_evidence_list_view, ocr_evidence_detail_view,
    # Reports
    arabic_report_view, download_pdf_report_view,
    reports_list_view, analytics_dashboard_view, resolve_insight_view,
    # Settings
    toggle_language_view, organization_settings_view,
)

urlpatterns = [
    # Auth
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    
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
    
    # Legacy views
    path('documents/', documents_view, name='documents'),
    path('analytics/', analytics_dashboard_view, name='analytics_dashboard'),
    path('insights/<uuid:insight_id>/resolve/', resolve_insight_view, name='resolve_insight'),
    
    # Organization Settings
    path('settings/organization/', organization_settings_view, name='organization_settings'),
]
