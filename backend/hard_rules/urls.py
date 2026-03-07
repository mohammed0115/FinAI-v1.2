"""
Hard Rules URL Configuration
"""
from django.urls import path
from . import views

app_name = 'hard_rules'

urlpatterns = [
    # Web Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Governance Status
    path('governance/status/', views.get_governance_status, name='governance-status'),
    path('governance/rules/', views.get_rule_enforcement_summary, name='rule-enforcement'),
    path('governance/health/', views.get_engine_health, name='engine-health'),
    
    # Validation Endpoints
    path('validate/invoice/', views.validate_invoice, name='validate-invoice'),
    path('validate/journal-entry/', views.validate_journal_entry, name='validate-journal-entry'),
    
    # AI Gate
    path('gate/check/', views.check_ai_gate, name='ai-gate-check'),
    
    # Evaluation History
    path('evaluations/', views.get_recent_evaluations, name='recent-evaluations'),
]
