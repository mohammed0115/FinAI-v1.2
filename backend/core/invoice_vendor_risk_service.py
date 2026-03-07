"""
Phase 4: Vendor Risk Intelligence Service

Calculates vendor-level risk metrics:
- Historical violation tracking
- Duplicate suspicion counts
- Anomaly aggregation
- Risk score and level calculation
"""

import logging
from datetime import timedelta, datetime
from django.db.models import Count, Q, Avg

from documents.models import ExtractedData, CrossDocumentFinding, VendorRisk

logger = logging.getLogger(__name__)


class InvoiceVendorRiskService:
    """Service for calculating vendor risk intelligence"""
    
    # Risk scoring weights
    ANOMALY_WEIGHT = 30
    DUPLICATE_WEIGHT = 40
    VIOLATION_WEIGHT = 35
    COMPLIANCE_WEIGHT = 25
    
    # Risk level thresholds
    CRITICAL_THRESHOLD = 75
    HIGH_THRESHOLD = 50
    MEDIUM_THRESHOLD = 25
    LOW_THRESHOLD = 0
    
    def calculate_vendor_risk(self, extracted_data):
        """
        Calculate risk for the vendor in this invoice
        
        Returns:
            VendorRisk instance (created or updated)
        """
        
        try:
            vendor_name = extracted_data.vendor_name
            
            if not vendor_name:
                return None
            
            # Get or create vendor risk record
            vendor_risk, created = VendorRisk.objects.get_or_create(
                organization=extracted_data.organization,
                vendor_name=vendor_name,
            )
            
            # Recalculate all metrics
            vendor_risk = self._recalculate_vendor_metrics(vendor_risk)
            vendor_risk.save()
            
            logger.info(f"Vendor risk updated for {vendor_name}: score={vendor_risk.risk_score}, level={vendor_risk.risk_level}")
            return vendor_risk
            
        except Exception as e:
            logger.error(f"Error calculating vendor risk: {str(e)}")
            return None
    
    def _recalculate_vendor_metrics(self, vendor_risk):
        """Recalculate all metrics for a vendor"""
        
        # Get all invoices from this vendor
        vendor_invoices = ExtractedData.objects.filter(
            organization=vendor_risk.organization,
            vendor_name__iexact=vendor_risk.vendor_name,
            extraction_status='extracted'
        )
        
        # Update basic counts
        vendor_risk.total_invoices = vendor_invoices.count()
        
        # Count duplicates
        vendor_risk.duplicate_suspicion_count = 0
        for inv in vendor_invoices:
            if inv.duplicate_score and inv.duplicate_score >= 60:
                vendor_risk.duplicate_suspicion_count += 1
        
        # Count anomalies
        vendor_risk.anomaly_count = 0
        for inv in vendor_invoices:
            anomalies = inv.cross_document_findings.filter(finding_type='*')
            vendor_risk.anomaly_count += len(anomalies)
        
        # Count compliance failures
        vendor_risk.compliance_failure_count = 0
        for inv in vendor_invoices:
            if inv.compliance_checks:
                for check in inv.compliance_checks:
                    if check.get('status') in ['INVALID', 'MISSING']:
                        vendor_risk.compliance_failure_count += 1
        
        # Count violations (failed findings)
        vendor_risk.violation_count = 0
        for inv in vendor_invoices:
            findings = inv.cross_document_findings.filter(status='confirmed')
            vendor_risk.violation_count += findings.count()
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(vendor_risk)
        vendor_risk.risk_score = risk_score
        
        # Assign risk level
        vendor_risk.risk_level = self._get_risk_level(risk_score)
        
        # Calculate risk factors as percentages
        total = vendor_risk.total_invoices if vendor_risk.total_invoices > 0 else 1
        vendor_risk.risk_factors = {
            'duplicate_risk_pct': (vendor_risk.duplicate_suspicion_count / total) * 100,
            'anomaly_rate': (vendor_risk.anomaly_count / total) * 100,
            'violation_rate': (vendor_risk.violation_count / total) * 100,
            'compliance_failure_rate': (vendor_risk.compliance_failure_count / total) * 100,
            'compliance_pass_rate': 100 - ((vendor_risk.compliance_failure_count / total) * 100),
        }
        
        # Track last issue dates
        vendor_risk.last_analyzed_at = datetime.now()
        
        # Find last violation date
        last_violation = ExtractedData.objects.filter(
            organization=vendor_risk.organization,
            vendor_name__iexact=vendor_risk.vendor_name,
            cross_document_findings__status='confirmed'
        ).order_by('-invoice_date').first()
        
        if last_violation:
            vendor_risk.last_violation_at = last_violation.invoice_date
        
        # Find last anomaly date
        last_anomaly = ExtractedData.objects.filter(
            organization=vendor_risk.organization,
            vendor_name__iexact=vendor_risk.vendor_name,
            cross_document_findings__isnull=False
        ).exclude(
            cross_document_findings__finding_type=''
        ).order_by('-invoice_date').first()
        
        if last_anomaly:
            vendor_risk.last_anomaly_at = last_anomaly.invoice_date
        
        # Build historical issues list
        historical_issues = []
        
        # Recent duplicates
        recent_duplicates = ExtractedData.objects.filter(
            organization=vendor_risk.organization,
            vendor_name__iexact=vendor_risk.vendor_name,
            duplicate_score__gte=75,
            extracted_at__gte=datetime.now() - timedelta(days=90)
        ).count()
        
        if recent_duplicates > 0:
            historical_issues.append({
                'type': 'duplicate_suspicion',
                'count': recent_duplicates,
                'period': 'last_90_days',
            })
        
        # Recent anomalies
        recent_anomalies = CrossDocumentFinding.objects.filter(
            organization=vendor_risk.organization,
            extracted_data__vendor_name__iexact=vendor_risk.vendor_name,
            created_at__gte=datetime.now() - timedelta(days=90)
        ).count()
        
        if recent_anomalies > 0:
            historical_issues.append({
                'type': 'anomalies',
                'count': recent_anomalies,
                'period': 'last_90_days',
            })
        
        # Recent compliance failures
        recent_failures = ExtractedData.objects.filter(
            organization=vendor_risk.organization,
            vendor_name__iexact=vendor_risk.vendor_name,
            is_valid=False,
            extracted_at__gte=datetime.now() - timedelta(days=90)
        ).count()
        
        if recent_failures > 0:
            historical_issues.append({
                'type': 'compliance_failures',
                'count': recent_failures,
                'period': 'last_90_days',
            })
        
        vendor_risk.historical_issues = historical_issues
        
        return vendor_risk
    
    def _calculate_risk_score(self, vendor_risk):
        """Calculate overall vendor risk score (0-100)"""
        
        if vendor_risk.total_invoices == 0:
            return 0
        
        # Normalize metrics to 0-100 scale
        total = vendor_risk.total_invoices
        
        duplicate_score = (vendor_risk.duplicate_suspicion_count / total) * 100
        anomaly_score = min(100, (vendor_risk.anomaly_count / max(total, 1)) * 100)
        violation_score = (vendor_risk.violation_count / total) * 100
        compliance_score = min(100, (vendor_risk.compliance_failure_count / total) * 100)
        
        # Weighted average
        total_weight = self.DUPLICATE_WEIGHT + self.ANOMALY_WEIGHT + self.VIOLATION_WEIGHT + self.COMPLIANCE_WEIGHT
        
        risk_score = (
            (duplicate_score * self.DUPLICATE_WEIGHT +
             anomaly_score * self.ANOMALY_WEIGHT +
             violation_score * self.VIOLATION_WEIGHT +
             compliance_score * self.COMPLIANCE_WEIGHT) /
            total_weight
        )
        
        # Cap at 100
        return min(100, int(risk_score))
    
    def _get_risk_level(self, risk_score):
        """Convert risk score to risk level"""
        if risk_score >= self.CRITICAL_THRESHOLD:
            return 'critical'
        elif risk_score >= self.HIGH_THRESHOLD:
            return 'high'
        elif risk_score >= self.MEDIUM_THRESHOLD:
            return 'medium'
        else:
            return 'low'
    
    def get_high_risk_vendors(self, organization, limit=10):
        """Get list of high-risk vendors"""
        return VendorRisk.objects.filter(
            organization=organization,
            risk_level__in=['high', 'critical']
        ).order_by('-risk_score')[:limit]
    
    def get_vendor_risk_summary(self, vendor_risk):
        """Generate human-readable risk summary"""
        
        parts = []
        
        if vendor_risk.risk_level == 'critical':
            parts.append(f"⚠️ CRITICAL: {vendor_risk.risk_score}/100")
        elif vendor_risk.risk_level == 'high':
            parts.append(f"⚠️ HIGH RISK: {vendor_risk.risk_score}/100")
        elif vendor_risk.risk_level == 'medium':
            parts.append(f"⚠ Medium Risk: {vendor_risk.risk_score}/100")
        else:
            parts.append(f"✓ Low Risk: {vendor_risk.risk_score}/100")
        
        # Add details
        if vendor_risk.duplicate_suspicion_count > 0:
            parts.append(f"{vendor_risk.duplicate_suspicion_count} duplicate suspicions")
        
        if vendor_risk.anomaly_count > 0:
            parts.append(f"{vendor_risk.anomaly_count} anomalies")
        
        if vendor_risk.violation_count > 0:
            parts.append(f"{vendor_risk.violation_count} violations")
        
        if vendor_risk.compliance_failure_count > 0:
            pct = (vendor_risk.compliance_failure_count / vendor_risk.total_invoices * 100) if vendor_risk.total_invoices > 0 else 0
            parts.append(f"{pct:.0f}% compliance failure rate")
        
        return " | ".join(parts)


# Singleton instance
invoice_vendor_risk_service = InvoiceVendorRiskService()

