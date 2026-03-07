"""
Core Views Package - حزمة وجهات النظر الأساسية

This package contains all web views split into focused modules:
- auth_views: Login, logout
- dashboard_views: Main dashboard
- compliance_views: ZATCA, VAT, Zakat compliance
- finding_views: Audit findings and AI explanations
- transaction_views: Transactions and accounts
- document_views: Document upload and OCR
- report_views: Reports and analytics
- settings_views: Organization settings
"""

# Import REST API ViewSets from the original views.py file
# These are used by core/urls.py for the REST API endpoints
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from core.models import User, Organization, AuditLog, Configuration
from core.serializers import UserSerializer, OrganizationSerializer, AuditLogSerializer, ConfigurationSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register new user"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by('name')
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Organization.objects.all().order_by('name')
        elif user.organization:
            return Organization.objects.filter(id=user.organization.id).order_by('name')
        return Organization.objects.none()
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get organization statistics"""
        org = self.get_object()
        
        from documents.models import Document, Transaction
        from reports.models import Report, Insight
        
        stats = {
            'total_documents': Document.objects.filter(organization=org).count(),
            'pending_documents': Document.objects.filter(organization=org, status='pending').count(),
            'total_transactions': Transaction.objects.filter(organization=org).count(),
            'unresolved_insights': Insight.objects.filter(organization=org, is_resolved=False).count(),
            'total_reports': Report.objects.filter(organization=org).count(),
            'users_count': User.objects.filter(organization=org).count(),
        }
        
        return Response(stats)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return AuditLog.objects.all()
        elif user.organization:
            return AuditLog.objects.filter(organization=user.organization)
        return AuditLog.objects.none()


class ConfigurationViewSet(viewsets.ModelViewSet):
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Configuration.objects.all()
        elif user.organization:
            return Configuration.objects.filter(Q(organization=user.organization) | Q(config_type='system'))
        return Configuration.objects.filter(config_type='system')

# Auth views
from .auth_views import (
    login_view,
    logout_view,
    register_view,
)

# Dashboard views
from .dashboard_views import (
    dashboard_view,
)

# Compliance views
from .compliance_views import (
    compliance_overview_view,
    zatca_verification_view,
)

# Finding views
from .finding_views import (
    audit_findings_list_view,
    audit_finding_detail_view,
    generate_ai_explanation_view,
    review_ai_explanation_view,
)

# Transaction views
from .transaction_views import (
    transactions_view,
    transaction_detail_view,
    accounts_list_view,
    account_detail_view,
)

# Document views
from .document_views import (
    documents_view,
    document_upload_view,
    process_pending_documents,
    ocr_evidence_list_view,
    ocr_evidence_detail_view,
    pipeline_result_view,
    pending_review_submit_view,
)

# Report views
from .report_views import (
    arabic_report_view,
    download_pdf_report_view,
    reports_list_view,
    analytics_dashboard_view,
    resolve_insight_view,
)

# Settings views
from .settings_views import (
    toggle_language_view,
    organization_settings_view,
)

__all__ = [
    # REST API ViewSets
    'UserViewSet',
    'OrganizationViewSet',
    'AuditLogViewSet',
    'ConfigurationViewSet',
    # Auth
    'login_view',
    'logout_view',
    'register_view',
    # Dashboard
    'dashboard_view',
    # Compliance
    'compliance_overview_view',
    'zatca_verification_view',
    # Findings
    'audit_findings_list_view',
    'audit_finding_detail_view',
    'generate_ai_explanation_view',
    'review_ai_explanation_view',
    # Transactions
    'transactions_view',
    'transaction_detail_view',
    'accounts_list_view',
    'account_detail_view',
    # Documents
    'documents_view',
    'document_upload_view',
    'process_pending_documents',
    'ocr_evidence_list_view',
    'ocr_evidence_detail_view',
    'pipeline_result_view',
    # Reports
    'arabic_report_view',
    'download_pdf_report_view',
    'reports_list_view',
    'analytics_dashboard_view',
    'resolve_insight_view',
    # Settings
    'toggle_language_view',
    'organization_settings_view',
]
