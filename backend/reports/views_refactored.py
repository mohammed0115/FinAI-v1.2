"""Refactored reports views using service layer.

Views delegate all business logic to service methods.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import datetime

from .models import Report, Insight
from .serializers import ReportSerializer, InsightSerializer
from .services import (
    ReportGenerationService,
    ReportStatusService,
    InsightService
)


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for report operations."""
    
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter reports based on user role and organization."""
        user = self.request.user
        if user.role == 'admin':
            return Report.objects.all()
        elif user.organization:
            return Report.objects.filter(organization=user.organization)
        return Report.objects.none()
    
    def perform_create(self, serializer):
        """Set generated_by to current user."""
        serializer.save(generated_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate a new financial report."""
        try:
            # Parse request data
            organization_id = request.data.get('organization_id')
            report_type = request.data.get('report_type')
            report_name = request.data.get('report_name')
            period_start = datetime.fromisoformat(request.data.get('period_start'))
            period_end = datetime.fromisoformat(request.data.get('period_end'))
            
            # Delegate to service
            report = ReportGenerationService.generate_report(
                organization_id=organization_id,
                report_type=report_type,
                report_name=report_name,
                period_start=period_start,
                period_end=period_end,
                generated_by=request.user
            )
            
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except (ValueError, KeyError) as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update report status."""
        report = self.get_object()
        new_status = request.data.get('status')
        
        # Delegate to service
        ReportStatusService.update_status(
            report=report,
            new_status=new_status,
            user=request.user
        )
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)


class InsightViewSet(viewsets.ModelViewSet):
    """ViewSet for insight operations."""
    
    queryset = Insight.objects.all()
    serializer_class = InsightSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter insights based on user role, organization, and resolution status."""
        user = self.request.user
        
        # Base queryset by role
        if user.role == 'admin':
            queryset = Insight.objects.all()
        else:
            queryset = Insight.objects.filter(organization=user.organization)
        
        # Filter by resolution status
        include_resolved = self.request.query_params.get(
            'include_resolved',
            'false'
        ).lower() == 'true'
        
        if not include_resolved:
            queryset = queryset.filter(is_resolved=False)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark insight as resolved."""
        insight = self.get_object()
        
        # Delegate to service
        InsightService.resolve_insight(
            insight=insight,
            resolved_by=request.user
        )
        
        serializer = self.get_serializer(insight)
        return Response(serializer.data)
