"""Refactored analytics views using service layer.

Views are thin controllers that delegate business logic to services.
"""
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .services import (
    ForecastService,
    AnomalyDetectionService,
    TrendAnalysisService,
    InsightGenerationService,
    KPIService
)


class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for analytics operations."""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def forecast(self, request):
        """Generate cash flow forecast."""
        organization_id = request.data.get('organization_id')
        periods = request.data.get('periods', 6)
        
        # Delegate to service
        forecast = ForecastService.generate_forecast(
            organization_id=organization_id,
            periods=periods
        )
        
        return Response({'forecast': forecast})
    
    @action(detail=False, methods=['post'])
    def detect_anomalies(self, request):
        """Detect anomalies in transactions."""
        organization_id = request.data.get('organization_id')
        
        # Delegate to service
        anomalies = AnomalyDetectionService.detect_and_save_anomalies(
            organization_id=organization_id
        )
        
        return Response({'anomalies': anomalies})
    
    @action(detail=False, methods=['post'])
    def analyze_trends(self, request):
        """Analyze financial trends."""
        organization_id = request.data.get('organization_id')
        metrics = request.data.get('metrics', ['revenue', 'expenses', 'profit'])
        
        # Delegate to service
        trends = TrendAnalysisService.analyze_trends(
            organization_id=organization_id,
            metrics=metrics
        )
        
        return Response({'trends': trends})
    
    @action(detail=False, methods=['post'])
    def generate_insights(self, request):
        """Generate comprehensive financial insights."""
        organization_id = request.data.get('organization_id')
        
        # Delegate to service
        insights = InsightGenerationService.generate_insights(
            organization_id=organization_id
        )
        
        return Response({'insights': insights})
    
    @action(detail=False, methods=['get'])
    def kpis(self, request):
        """Calculate financial KPIs."""
        organization_id = request.query_params.get('organization_id')
        period = request.query_params.get('period', 'month')
        
        # Delegate to service
        kpis = KPIService.calculate_kpis(
            organization_id=organization_id,
            period=period
        )
        
        return Response(kpis)
