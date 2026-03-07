"""
Monitoring and Dashboard Views
Real-time monitoring dashboard endpoints for document processing
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Avg, Sum, Q
from core.monitoring import (
    DocumentProcessingMetrics,
    OCRPerformanceMetrics,
    ComplianceMetrics,
    RiskScoringMetrics,
    SystemHealthMetrics,
)
from documents.models import Document, OCREvidence
from compliance.models import AuditFinding
import logging

logger = logging.getLogger(__name__)


class MonitoringViewSet(viewsets.ViewSet):
    """API endpoints for monitoring and metrics"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def system_health(self, request):
        """Get overall system health status"""
        try:
            health = SystemHealthMetrics.get_system_health()
            return Response(health)
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def document_stats(self, request):
        """Get document processing statistics"""
        try:
            org_id = request.query_params.get('organization_id')
            days = int(request.query_params.get('days', 7))
            
            stats = DocumentProcessingMetrics.get_processing_stats(org_id, days)
            daily_stats = DocumentProcessingMetrics.get_daily_stats(org_id)
            queue_status = DocumentProcessingMetrics.get_processing_queue_status()
            
            return Response({
                'overall': stats,
                'daily': daily_stats,
                'queue': queue_status,
            })
        except Exception as e:
            logger.error(f"Error getting document stats: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def ocr_performance(self, request):
        """Get OCR performance metrics"""
        try:
            org_id = request.query_params.get('organization_id')
            days = int(request.query_params.get('days', 7))
            
            stats = OCRPerformanceMetrics.get_ocr_stats(org_id, days)
            detailed = OCRPerformanceMetrics.get_extraction_detailed_stats()
            
            return Response({
                'overall': stats,
                'extraction_accuracy': detailed,
            })
        except Exception as e:
            logger.error(f"Error getting OCR stats: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def compliance_stats(self, request):
        """Get compliance check statistics"""
        try:
            org_id = request.query_params.get('organization_id')
            days = int(request.query_params.get('days', 7))
            
            stats = ComplianceMetrics.get_compliance_stats(org_id, days)
            by_rule = ComplianceMetrics.get_compliance_by_rule()
            
            return Response({
                'overall': stats,
                'by_rule': by_rule,
            })
        except Exception as e:
            logger.error(f"Error getting compliance stats: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def risk_metrics(self, request):
        """Get risk assessment metrics"""
        try:
            distribution = RiskScoringMetrics.get_risk_distribution()
            trends = RiskScoringMetrics.get_risk_trends()
            
            return Response({
                'distribution': distribution,
                'trends': trends,
            })
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Get comprehensive dashboard summary"""
        try:
            org_id = request.query_params.get('organization_id')
            
            doc_stats = DocumentProcessingMetrics.get_processing_stats(org_id, 7)
            ocr_stats = OCRPerformanceMetrics.get_ocr_stats(org_id, 7)
            compliance_stats = ComplianceMetrics.get_compliance_stats(org_id, 7)
            risk_dist = RiskScoringMetrics.get_risk_distribution()
            health = SystemHealthMetrics.get_system_health()
            
            return Response({
                'timestamp': health['timestamp'],
                'health_status': health['status'],
                'documents': {
                    'total': doc_stats['total_documents'],
                    'success_rate': doc_stats['success_rate'],
                    'avg_processing_time_ms': doc_stats['avg_processing_time_ms'],
                },
                'ocr': {
                    'avg_confidence': ocr_stats['average_confidence'],
                    'high_confidence_count': ocr_stats['high_confidence'],
                    'extraction_accuracy': OCRPerformanceMetrics.get_extraction_detailed_stats(),
                },
                'compliance': {
                    'total_checks': compliance_stats['total_checks'],
                    'critical_issues': compliance_stats['critical_issues'],
                    'high_issues': compliance_stats['high_issues'],
                    'pass_rate': round(
                        (compliance_stats['passed_checks'] / compliance_stats['total_checks']) * 100, 1
                        if compliance_stats['total_checks'] > 0 else 0
                    ),
                },
                'risk': risk_dist,
                'alerts': health['alerts'],
            })
        except Exception as e:
            logger.error(f"Error generating dashboard summary: {e}")
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# Web Views for Dashboard HTML UI

@login_required
@require_http_methods(["GET"])
def monitoring_dashboard_view(request):
    """Main monitoring dashboard view"""
    try:
        org = request.user.organization
        
        # Get all metrics
        doc_stats = DocumentProcessingMetrics.get_processing_stats(org.id, 7)
        daily_stats = DocumentProcessingMetrics.get_daily_stats(org.id)
        queue_status = DocumentProcessingMetrics.get_processing_queue_status()
        ocr_stats = OCRPerformanceMetrics.get_ocr_stats(org.id, 7)
        compliance_stats = ComplianceMetrics.get_compliance_stats(org.id, 7)
        health = SystemHealthMetrics.get_system_health()
        
        context = {
            'page_title': 'Monitoring Dashboard',
            'health_status': health['status'],
            'doc_stats': doc_stats,
            'daily_stats': daily_stats,
            'queue_status': queue_status,
            'ocr_stats': ocr_stats,
            'compliance_stats': compliance_stats,
            'alerts': health['alerts'],
            'timestamp': health['timestamp'],
        }
        
        return render(request, 'monitoring/dashboard.html', context)
    except Exception as e:
        logger.error(f"Error rendering monitoring dashboard: {e}")
        return render(request, 'monitoring/dashboard.html', {
            'error': str(e),
            'alerts': [{'level': 'error', 'message': str(e)}]
        }, status=500)


@login_required
@require_http_methods(["GET"])
def processing_pipeline_view(request):
    """Document processing pipeline visualization"""
    try:
        org = request.user.organization
        
        # Get detailed processing stages
        documents = Document.objects.filter(organization=org).order_by('-uploaded_at')[:50]
        
        context = {
            'page_title': 'Processing Pipeline',
            'documents': documents,
            'stats': DocumentProcessingMetrics.get_processing_queue_status(),
        }
        
        return render(request, 'monitoring/pipeline.html', context)
    except Exception as e:
        logger.error(f"Error rendering pipeline view: {e}")
        return render(request, 'monitoring/pipeline.html', {
            'error': str(e),
        }, status=500)


@login_required
@require_http_methods(["GET"])
def ocr_metrics_view(request):
    """OCR performance metrics page"""
    try:
        org = request.user.organization
        
        stats = OCRPerformanceMetrics.get_ocr_stats(org.id, 7)
        detailed = OCRPerformanceMetrics.get_extraction_detailed_stats()
        
        context = {
            'page_title': 'OCR Metrics',
            'stats': stats,
            'extraction_accuracy': detailed,
        }
        
        return render(request, 'monitoring/ocr_metrics.html', context)
    except Exception as e:
        logger.error(f"Error rendering OCR metrics: {e}")
        return render(request, 'monitoring/ocr_metrics.html', {
            'error': str(e),
        }, status=500)


@login_required
@require_http_methods(["GET"])
def compliance_report_view(request):
    """Compliance check report page"""
    try:
        org = request.user.organization
        
        stats = ComplianceMetrics.get_compliance_stats(org.id, 7)
        by_rule = ComplianceMetrics.get_compliance_by_rule()
        
        context = {
            'page_title': 'Compliance Report',
            'stats': stats,
            'by_rule': by_rule,
        }
        
        return render(request, 'monitoring/compliance_report.html', context)
    except Exception as e:
        logger.error(f"Error rendering compliance report: {e}")
        return render(request, 'monitoring/compliance_report.html', {
            'error': str(e),
        }, status=500)


@login_required
@require_http_methods(["GET"])
def risk_dashboard_view(request):
    """Risk assessment dashboard"""
    try:
        distribution = RiskScoringMetrics.get_risk_distribution()
        trends = RiskScoringMetrics.get_risk_trends()
        
        context = {
            'page_title': 'Risk Dashboard',
            'risk_distribution': distribution,
            'risk_trends': trends,
        }
        
        return render(request, 'monitoring/risk_dashboard.html', context)
    except Exception as e:
        logger.error(f"Error rendering risk dashboard: {e}")
        return render(request, 'monitoring/risk_dashboard.html', {
            'error': str(e),
        }, status=500)
