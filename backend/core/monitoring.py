"""
FinAI Monitoring System - Real-time metrics and health tracking
Tracks document processing pipeline, OCR performance, compliance checks, and system health
"""

import logging
from datetime import datetime, timedelta
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from documents.models import Document, OCREvidence
from compliance.models import AuditFinding
from core.models import Organization
from decimal import Decimal

logger = logging.getLogger(__name__)


class DocumentProcessingMetrics:
    """Tracks document processing metrics"""
    
    @staticmethod
    def get_processing_stats(organization_id=None, days=7):
        """Get document processing statistics"""
        query = Document.objects.all()
        if organization_id:
            query = query.filter(organization_id=organization_id)
        
        # Filter by date range
        date_threshold = timezone.now() - timedelta(days=days)
        query_recent = query.filter(uploaded_at__gte=date_threshold)
        
        # Calculate processing time from documents that have been processed
        processed_docs = query_recent.filter(processed_at__isnull=False)
        if processed_docs.count() > 0:
            # Estimate average processing time from upload to process_at
            processing_times = []
            for doc in processed_docs:
                if doc.processed_at and doc.uploaded_at:
                    proc_time = int((doc.processed_at - doc.uploaded_at).total_seconds() * 1000)
                    processing_times.append(proc_time)
            avg_processing = int(sum(processing_times) / len(processing_times)) if processing_times else 0
        else:
            avg_processing = 0
        
        stats = {
            'total_documents': query_recent.count(),
            'documents_by_status': dict(
                query_recent.values('status').annotate(count=Count('id')).values_list('status', 'count')
            ),
            'documents_by_type': dict(
                query_recent.values('document_type').annotate(count=Count('id')).values_list('document_type', 'count')
            ),
            'avg_processing_time_ms': avg_processing,
            'total_file_size_mb': float(
                (query_recent.aggregate(total=Sum('file_size'))['total'] or 0) / (1024 * 1024)
            ),
            'success_rate': calculate_success_rate(query_recent),
            'average_confidence': get_average_ocr_confidence(query_recent),
        }
        
        return stats
    
    @staticmethod
    def get_daily_stats(organization_id=None):
        """Get stats for each day in the last 7 days"""
        daily_stats = []
        
        for i in range(7, -1, -1):
            date = (timezone.now() - timedelta(days=i)).date()
            query = Document.objects.filter(uploaded_at__date=date)
            
            if organization_id:
                query = query.filter(organization_id=organization_id)
            
            daily_stats.append({
                'date': date.isoformat(),
                'uploaded': query.count(),
                'processed': query.filter(status='completed').count(),
                'failed': query.filter(status='failed').count(),
                'pending': query.filter(status__in=['pending', 'processing']).count(),
            })
        
        return daily_stats
    
    @staticmethod
    def get_processing_queue_status():
        """Get status of documents in processing queue"""
        return {
            'pending': Document.objects.filter(status='pending').count(),
            'processing': Document.objects.filter(status='processing').count(),
            'completed': Document.objects.filter(status='completed').count(),
            'failed': Document.objects.filter(status='failed').count(),
            'oldest_pending': get_oldest_pending_document(),
        }


class OCRPerformanceMetrics:
    """Tracks OCR extraction performance"""
    
    @staticmethod
    def get_ocr_stats(organization_id=None, days=7):
        """Get OCR performance metrics"""
        query = OCREvidence.objects.all()
        if organization_id:
            query = query.filter(organization_id=organization_id)
        
        date_threshold = timezone.now() - timedelta(days=days)
        query = query.filter(extracted_at__gte=date_threshold)
        
        confidence_data = query.aggregate(
            avg_confidence=Avg('confidence_score'),
            max_confidence=Count('confidence_score', filter=Q(confidence_score__gte=80)),
            medium_confidence=Count('confidence_score', filter=Q(confidence_score__gte=60, confidence_score__lt=80)),
            low_confidence=Count('confidence_score', filter=Q(confidence_score__lt=60)),
        )
        
        stats = {
            'total_extractions': query.count(),
            'average_confidence': round(confidence_data.get('avg_confidence') or 0, 2),
            'high_confidence': confidence_data.get('max_confidence', 0),
            'medium_confidence': confidence_data.get('medium_confidence', 0),
            'low_confidence': confidence_data.get('low_confidence', 0),
            'avg_processing_time_ms': int(
                query.aggregate(avg=Avg('processing_time_ms'))['avg'] or 0
            ),
            'avg_page_count': round(
                query.aggregate(avg=Avg('page_count'))['avg'] or 1, 1
            ),
            'avg_word_count': int(
                query.aggregate(avg=Avg('word_count'))['avg'] or 0
            ),
            'engine_distribution': dict(
                query.values('ocr_engine').annotate(count=Count('id')).values_list('ocr_engine', 'count')
            ),
        }
        
        return stats
    
    @staticmethod
    def get_extraction_detailed_stats():
        """Get detailed extraction statistics"""
        recent_evidence = OCREvidence.objects.order_by('-created_at')[:100]
        
        extracted_fields = {
            'invoice_number': recent_evidence.filter(extracted_invoice_number__isnull=False).count(),
            'vat_number': recent_evidence.filter(extracted_vat_number__isnull=False).count(),
            'total_amount': recent_evidence.filter(extracted_total__isnull=False).count(),
            'tax_amount': recent_evidence.filter(extracted_tax__isnull=False).count(),
        }
        
        field_accuracy = {
            field: round((count / len(recent_evidence)) * 100, 1) if recent_evidence else 0
            for field, count in extracted_fields.items()
        }
        
        return field_accuracy


class ComplianceMetrics:
    """Tracks compliance check metrics"""
    
    @staticmethod
    def get_compliance_stats(organization_id=None, days=7):
        """Get compliance check statistics"""
        query = AuditFinding.objects.all()
        if organization_id:
            query = query.filter(organization_id=organization_id)
        
        date_threshold = timezone.now() - timedelta(days=days)
        query = query.filter(created_at__gte=date_threshold)
        
        stats = {
            'total_checks': query.count(),
            'checks_by_status': dict(
                query.values('is_resolved').annotate(count=Count('id')).values_list('is_resolved', 'count')
            ),
            'checks_by_severity': dict(
                query.values('risk_level').annotate(count=Count('id')).values_list('risk_level', 'count')
            ),
            'critical_issues': query.filter(risk_level='critical').count(),
            'high_issues': query.filter(risk_level='high').count(),
            'passed_checks': query.filter(is_resolved=True).count(),
            'failed_checks': query.filter(is_resolved=False).count(),
            'avg_issues_per_document': calculate_avg_issues_from_findings(query),
        }
        
        return stats
    
    @staticmethod
    def get_compliance_by_rule():
        """Get compliance check results by finding type"""
        rule_stats = AuditFinding.objects.values('finding_type').annotate(
            total=Count('id'),
            resolved=Count('id', filter=Q(is_resolved=True)),
            unresolved=Count('id', filter=Q(is_resolved=False)),
        ).order_by('-total')
        
        return [
            {
                'rule': item['finding_type'],
                'total': item['total'],
                'resolved': item['resolved'],
                'unresolved': item['unresolved'],
                'resolution_rate': round((item['resolved'] / item['total']) * 100, 1) if item['total'] > 0 else 0,
            }
            for item in rule_stats
        ]


class RiskScoringMetrics:
    """Tracks risk assessment metrics"""
    
    @staticmethod
    def get_risk_distribution():
        """Get distribution of risk scores/levels from findings"""
        risk_data = AuditFinding.objects.aggregate(
            critical=Count('id', filter=Q(risk_level='critical')),
            high=Count('id', filter=Q(risk_level='high')),
            medium=Count('id', filter=Q(risk_level='medium')),
            low=Count('id', filter=Q(risk_level='low')),
            avg_confidence=Avg('ai_confidence'),
        )
        
        return risk_data
    
    @staticmethod
    def get_risk_trends(days=7):
        """Get risk trends over time from findings"""
        trends = []
        for i in range(days, -1, -1):
            date = (timezone.now() - timedelta(days=i)).date()
            
            daily_findings = AuditFinding.objects.filter(
                created_at__date=date
            )
            
            critical_count = daily_findings.filter(risk_level='critical').count()
            high_count = daily_findings.filter(risk_level='high').count()
            
            avg_risk_score = ((critical_count * 100 + high_count * 75) / max(daily_findings.count() or 1, 1)) if daily_findings.count() > 0 else 0
            
            trends.append({
                'date': date.isoformat(),
                'critical_count': critical_count,
                'high_count': high_count,
                'avg_risk_score': round(avg_risk_score, 2),
            })
        
        return trends


class SystemHealthMetrics:
    """Tracks overall system health"""
    
    @staticmethod
    def get_system_health():
        """Get comprehensive system health status"""
        doc_stats = DocumentProcessingMetrics.get_processing_queue_status()
        ocr_stats = OCRPerformanceMetrics.get_ocr_stats()
        
        health = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'metrics': {
                'documents_in_queue': doc_stats['pending'] + doc_stats['processing'],
                'processor_efficiency': calculate_processor_efficiency(),
                'ocr_average_confidence': ocr_stats['average_confidence'],
                'system_uptime_hours': get_system_uptime(),
            },
            'alerts': get_system_alerts(),
        }
        
        # Determine overall health
        if doc_stats['pending'] > 100:
            health['status'] = 'warning'
        if doc_stats['failed'] > (doc_stats['completed'] / 10):
            health['status'] = 'warning'
        if ocr_stats['average_confidence'] < 60:
            health['status'] = 'warning'
        
        return health


# Helper functions

def calculate_success_rate(queryset):
    """Calculate success rate percentage"""
    total = queryset.count()
    completed = queryset.filter(status='completed').count()
    return round((completed / total) * 100, 1) if total > 0 else 0


def get_average_ocr_confidence(queryset):
    """Get average OCR confidence for documents"""
    avg_confidence = OCREvidence.objects.filter(
        document__in=queryset
    ).aggregate(avg=Avg('confidence_score'))['avg'] or 0
    
    return round(avg_confidence, 2)


def get_oldest_pending_document():
    """Get oldest pending document in queue"""
    doc = Document.objects.filter(
        status__in=['pending', 'processing']
    ).order_by('uploaded_at').first()
    
    if doc:
        wait_time = timezone.now() - doc.uploaded_at
        return {
            'id': str(doc.id),
            'name': doc.file_name,
            'uploaded_at': doc.uploaded_at.isoformat(),
            'wait_minutes': int(wait_time.total_seconds() / 60),
        }
    return None


def calculate_avg_issues_from_findings(queryset):
    """Calculate average compliance issues per document from findings"""
    doc_count = queryset.values('related_entity_id').distinct().count()
    total_issues = queryset.count()
    return round(total_issues / doc_count, 2) if doc_count > 0 else 0


def calculate_processor_efficiency():
    """Calculate how efficiently documents are being processed"""
    completed = Document.objects.filter(status='completed').count()
    total = Document.objects.count()
    return round((completed / total) * 100, 1) if total > 0 else 0


def get_system_uptime():
    """Get approximate system uptime"""
    oldest_doc = Document.objects.order_by('uploaded_at').first()
    if oldest_doc:
        uptime = timezone.now() - oldest_doc.uploaded_at
        return round(uptime.total_seconds() / 3600, 1)
    return 0


def get_system_alerts():
    """Get current system alerts"""
    alerts = []
    
    # Check queue depth
    pending_count = Document.objects.filter(status='pending').count()
    if pending_count > 50:
        alerts.append({
            'level': 'warning',
            'message': f'{pending_count} documents waiting in queue',
            'timestamp': timezone.now().isoformat(),
        })
    
    # Check failure rate
    recent_docs = Document.objects.filter(
        uploaded_at__gte=timezone.now() - timedelta(hours=1)
    )
    if recent_docs.count() > 0:
        failure_rate = (recent_docs.filter(status='failed').count() / recent_docs.count()) * 100
        if failure_rate > 20:
            alerts.append({
                'level': 'warning',
                'message': f'Failure rate: {failure_rate:.1f}% in last hour',
                'timestamp': timezone.now().isoformat(),
            })
    
    # Check OCR confidence
    avg_confidence = OCREvidence.objects.filter(
        extracted_at__gte=timezone.now() - timedelta(hours=1)
    ).aggregate(avg=Avg('confidence_score'))['avg'] or 0
    
    if avg_confidence < 50:
        alerts.append({
            'level': 'warning',
            'message': f'Low OCR confidence: {avg_confidence:.1f}%',
            'timestamp': timezone.now().isoformat(),
        })
    
    return alerts
