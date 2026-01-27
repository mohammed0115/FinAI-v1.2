from django.urls import path
from . import web_views

urlpatterns = [
    # Auth
    path('login/', web_views.login_view, name='login'),
    path('logout/', web_views.logout_view, name='logout'),
    
    # Dashboard
    path('', web_views.dashboard_view, name='dashboard'),
    
    # Compliance
    path('compliance/', web_views.compliance_overview_view, name='compliance_overview'),
    
    # Audit Findings
    path('findings/', web_views.audit_findings_list_view, name='audit_findings_list'),
    path('findings/<uuid:finding_id>/', web_views.audit_finding_detail_view, name='audit_finding_detail'),
    path('findings/<uuid:finding_id>/generate-ai/', web_views.generate_ai_explanation_view, name='generate_ai_explanation'),
    
    # Transactions
    path('transactions/', web_views.transactions_view, name='transactions'),
    path('transactions/<uuid:transaction_id>/', web_views.transaction_detail_view, name='transaction_detail'),
    
    # Accounts
    path('accounts/', web_views.accounts_list_view, name='accounts_list'),
    path('accounts/<uuid:account_id>/', web_views.account_detail_view, name='account_detail'),
    
    # Reports
    path('reports/', web_views.reports_list_view, name='reports_list'),
    path('report/arabic/', web_views.arabic_report_view, name='arabic_report'),
    path('report/pdf/', web_views.download_pdf_report_view, name='download_pdf_report'),
    
    # Document OCR
    path('documents/upload/', web_views.document_upload_view, name='document_upload'),
    path('ocr/', web_views.ocr_evidence_list_view, name='ocr_evidence_list'),
    path('ocr/<uuid:evidence_id>/', web_views.ocr_evidence_detail_view, name='ocr_evidence_detail'),
    
    # Legacy views
    path('documents/', web_views.documents_view, name='documents'),
    path('analytics/', web_views.analytics_dashboard_view, name='analytics_dashboard'),
    path('insights/<uuid:insight_id>/resolve/', web_views.resolve_insight_view, name='resolve_insight'),
]
