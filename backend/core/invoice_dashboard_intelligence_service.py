"""
Phase 4: Dashboard Intelligence Service

Aggregates data for critical invoices dashboard:
- Suspected duplicates
- High-risk invoices  
- Vendor risk ranking
- Anomaly category breakdown
"""

import logging
from datetime import timedelta, datetime
from django.db.models import Count, Q, Avg, Max

from documents.models import ExtractedData, CrossDocumentFinding, VendorRisk

logger = logging.getLogger(__name__)


class InvoiceDashboardIntelligenceService:
    """Service for aggregating dashboard intelligence"""
    
    def get_critical_invoices_dashboard(self, organization, days=30, limit=50):
        """
        Get list of critical/high-risk invoices
        
        Returns:
            {
                'critical_invoices': [...],
                'high_risk_invoices': [...],
                'suspected_duplicates': [...],
                'summary': {...}
            }
        """
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Get critical invoices (risk_level = critical, or critical findings)
            critical = ExtractedData.objects.filter(
                organization=organization,
                risk_level='Critical',
                extracted_at__gte=since_date
            ).order_by('-risk_score')[:limit]
            
            # Get high-risk invoices
            high_risk = ExtractedData.objects.filter(
                organization=organization,
                risk_level__in=['High', 'high'],
                extracted_at__gte=since_date
            ).order_by('-risk_score')[:limit]
            
            # Get suspected duplicates
            suspected_dup = ExtractedData.objects.filter(
                organization=organization,
                duplicate_score__gte=75,
                extracted_at__gte=since_date
            ).order_by('-duplicate_score')[:limit]
            
            # Build summary
            summary = {
                'period_days': days,
                'critical_count': critical.count(),
                'high_risk_count': high_risk.count(),
                'duplicate_suspects': suspected_dup.count(),
                'total_anomalies': CrossDocumentFinding.objects.filter(
                    organization=organization,
                    created_at__gte=since_date
                ).count(),
                'vendors_at_risk': VendorRisk.objects.filter(
                    organization=organization,
                    risk_level__in=['high', 'critical']
                ).count(),
            }
            
            result = {
                'critical_invoices': self._format_invoice_list(critical),
                'high_risk_invoices': self._format_invoice_list(high_risk),
                'suspected_duplicates': self._format_invoice_list(suspected_dup),
                'summary': summary,
            }
            
            logger.info(f"Dashboard: {summary['critical_count']} critical, {summary['high_risk_count']} high-risk")
            return result
            
        except Exception as e:
            logger.error(f"Error generating dashboard: {str(e)}")
            return {
                'critical_invoices': [],
                'high_risk_invoices': [],
                'suspected_duplicates': [],
                'summary': {'error': str(e)},
            }
    
    def get_vendor_risk_ranking(self, organization, limit=20):
        """Get ranked list of vendors by risk"""
        
        try:
            vendors = VendorRisk.objects.filter(
                organization=organization
            ).order_by('-risk_score')[:limit]
            
            return [
                {
                    'vendor_name': v.vendor_name,
                    'risk_score': v.risk_score,
                    'risk_level': v.risk_level,
                    'total_invoices': v.total_invoices,
                    'duplicate_count': v.duplicate_suspicion_count,
                    'anomaly_count': v.anomaly_count,
                    'violation_count': v.violation_count,
                    'compliance_failure_rate': v.risk_factors.get('compliance_failure_rate', 0) if v.risk_factors else 0,
                }
                for v in vendors
            ]
        
        except Exception as e:
            logger.error(f"Error ranking vendors: {str(e)}")
            return []
    
    def get_anomaly_breakdown(self, organization, days=30):
        """Get breakdown of anomalies by category"""
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            findings = CrossDocumentFinding.objects.filter(
                organization=organization,
                created_at__gte=since_date
            )
            
            # Count by type
            by_type = {}
            for finding in findings:
                ftype = finding.finding_type
                by_type[ftype] = by_type.get(ftype, 0) + 1
            
            # Count by severity
            by_severity = {}
            for finding in findings:
                severity = finding.severity
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Count resolved vs open
            resolved = findings.filter(is_resolved=True).count()
            open_findings = findings.filter(is_resolved=False).count()
            
            total = findings.count()
            
            return {
                'period_days': days,
                'total_findings': total,
                'by_type': by_type,
                'by_severity': by_severity,
                'resolved': resolved,
                'open': open_findings,
                'resolution_rate': (resolved / total * 100) if total > 0 else 0,
            }
        
        except Exception as e:
            logger.error(f"Error getting anomaly breakdown: {str(e)}")
            return {
                'error': str(e),
            }
    
    def get_duplicate_detection_stats(self, organization, days=30):
        """Get duplicate detection statistics"""
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Count invoices checked
            total_checked = ExtractedData.objects.filter(
                organization=organization,
                extracted_at__gte=since_date,
                extraction_status='extracted'
            ).count()
            
            # Count suspected duplicates
            suspected = ExtractedData.objects.filter(
                organization=organization,
                extracted_at__gte=since_date,
                duplicate_score__gte=60
            ).count()
            
            # Count confirmed duplicates (from findings)
            confirmed = CrossDocumentFinding.objects.filter(
                organization=organization,
                finding_type='potential_duplicate',
                status='confirmed',
                created_at__gte=since_date
            ).count()
            
            return {
                'period_days': days,
                'total_checked': total_checked,
                'suspected': suspected,
                'confirmed': confirmed,
                'suspected_rate': (suspected / total_checked * 100) if total_checked > 0 else 0,
            }
        
        except Exception as e:
            logger.error(f"Error getting duplicate stats: {str(e)}")
            return {'error': str(e)}
    
    def get_compliance_dashboard(self, organization, days=30):
        """Get compliance status dashboard"""
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            invoices = ExtractedData.objects.filter(
                organization=organization,
                extracted_at__gte=since_date,
                extraction_status='extracted'
            )
            
            total = invoices.count()
            valid = invoices.filter(is_valid=True).count()
            invalid = invoices.filter(is_valid=False).count()
            
            # By risk level
            by_risk = {}
            for inv in invoices:
                risk = inv.risk_level or 'Unknown'
                by_risk[risk] = by_risk.get(risk, 0) + 1
            
            return {
                'period_days': days,
                'total_invoices': total,
                'valid': valid,
                'invalid': invalid,
                'validity_rate': (valid / total * 100) if total > 0 else 0,
                'by_risk_level': by_risk,
            }
        
        except Exception as e:
            logger.error(f"Error getting compliance dashboard: {str(e)}")
            return {'error': str(e)}
    
    def _format_invoice_list(self, invoices):
        """Format invoice list for API response"""
        
        results = []
        for inv in invoices:
            results.append({
                'id': str(inv.id),
                'invoice_number': inv.invoice_number,
                'vendor_name': inv.vendor_name,
                'customer_name': inv.customer_name,
                'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else None,
                'total_amount': str(inv.total_amount),
                'currency': inv.currency,
                'risk_score': inv.risk_score,
                'risk_level': inv.risk_level,
                'duplicate_score': inv.duplicate_score,
                'anomaly_score': inv.anomaly_score,
                'findings_count': inv.cross_document_findings.count(),
            })
        
        return results
    
    def get_trend_analysis(self, organization, days=90):
        """Get trend analysis for anomalies and findings"""
        
        try:
            since_date = datetime.now() - timedelta(days=days)
            
            # Weekly breakdown
            weeks = {}
            
            findings = CrossDocumentFinding.objects.filter(
                organization=organization,
                created_at__gte=since_date
            ).order_by('created_at')
            
            for finding in findings:
                week_start = finding.created_at - timedelta(days=finding.created_at.weekday())
                week_key = week_start.strftime('%Y-W%U')
                
                if week_key not in weeks:
                    weeks[week_key] = {
                        'start_date': week_start.date(),
                        'critical': 0,
                        'high': 0,
                        'medium': 0,
                        'low': 0,
                        'total': 0,
                    }
                
                weeks[week_key][finding.severity] += 1
                weeks[week_key]['total'] += 1
            
            return {
                'period_days': days,
                'total_findings': len(findings),
                'weekly_trend': sorted(weeks.items()),
            }
        
        except Exception as e:
            logger.error(f"Error getting trend analysis: {str(e)}")
            return {'error': str(e)}


# Singleton instance
invoice_dashboard_intelligence_service = InvoiceDashboardIntelligenceService()

