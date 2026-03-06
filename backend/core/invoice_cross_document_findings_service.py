"""
Phase 4: Cross-Document Findings Service

Creates structured CrossDocumentFinding records from:
- Duplicate detection results
- Cross-document validation anomalies
- Anomaly detection results

Manages finding lifecycle: creation, confirmation, resolution
"""

import logging
from documents.models import ExtractedData, CrossDocumentFinding

logger = logging.getLogger(__name__)


class InvoiceCrossDocumentFindingsService:
    """Service for managing cross-document findings"""
    
    # Finding type mapping from anomalies
    ANOMALY_TO_FINDING_TYPE = {
        'potential_duplicate': 'potential_duplicate',
        'amount_spike': 'unusual_amount',
        'amount_drop': 'unusual_amount',
        'suspicious_discount': 'suspicious_discount',
        'vat_inconsistency': 'vat_inconsistency',
        'frequency_anomaly': 'frequency_anomaly',
        'vendor_pattern_break': 'vendor_pattern_break',
        'cross_vendor_match': 'cross_vendor_match',
    }
    
    # Severity mapping
    ANOMALY_SEVERITY_MAP = {
        'critical': 'critical',
        'high': 'high',
        'medium': 'medium',
        'warning': 'medium',
        'low': 'low',
        'info': 'low',
    }
    
    def create_findings_from_duplicates(self, extracted_data, duplicate_matches):
        """Create findings from duplicate detection"""
        findings = []
        
        if not duplicate_matches:
            return findings
        
        try:
            for match in duplicate_matches:
                if match.score >= 60:  # Only create for significant matches
                    finding = CrossDocumentFinding.objects.create(
                        extracted_data=extracted_data,
                        organization=extracted_data.organization,
                        finding_type='potential_duplicate',
                        severity='critical' if match.score >= 90 else ('high' if match.score >= 75 else 'medium'),
                        title=f"Potential Duplicate Invoice Detected",
                        description=f"This invoice appears to be a duplicate of {match.matched_document.invoice_number} "
                                    f"({match.matched_document.vendor_name}). Duplicate confidence: {match.score}%.",
                        matched_document=match.matched_document,
                        confidence_score=match.score,
                        analysis_details={
                            'match_score': match.score,
                            'match_reasons': match.match_reasons,
                            'matched_invoice_id': str(match.matched_document.id),
                            'matched_invoice_number': match.matched_document.invoice_number,
                            'matched_vendor': match.matched_document.vendor_name,
                            'matched_date': match.matched_document.invoice_date.isoformat() if match.matched_document.invoice_date else None,
                            'matched_amount': str(match.matched_document.total_amount),
                        },
                        status='open',
                    )
                    findings.append(finding)
                    logger.info(f"Created duplicate finding for {extracted_data.invoice_number}: score={match.score}")
        
        except Exception as e:
            logger.error(f"Error creating duplicate findings: {str(e)}")
        
        return findings
    
    def create_findings_from_anomalies(self, extracted_data, anomaly_flags):
        """Create findings from detected anomalies"""
        findings = []
        
        if not anomaly_flags:
            return findings
        
        try:
            # Group anomalies by type
            by_type = {}
            for flag in anomaly_flags:
                atype = flag['type']
                if atype not in by_type:
                    by_type[atype] = []
                by_type[atype].append(flag)
            
            # Create one finding per anomaly type
            for anomaly_type, flags in by_type.items():
                # Skip duplicates (handled separately)
                if anomaly_type == 'potential_duplicate':
                    continue
                
                finding_type = self.ANOMALY_TO_FINDING_TYPE.get(anomaly_type, anomaly_type)
                severity = self.ANOMALY_SEVERITY_MAP.get(flags[0].get('severity', 'medium'), 'medium')
                
                # Build description
                descriptions = []
                max_score = 0
                for flag in flags:
                    descriptions.append(flag.get('description', ''))
                    max_score = max(max_score, flag.get('score', 0))
                
                description = " | ".join(descriptions) if descriptions else f"Detected {anomaly_type}"
                
                # Determine title
                title_map = {
                    'unusual_amount': 'Unusual Amount Change',
                    'vat_inconsistency': 'VAT Inconsistency',
                    'suspicious_discount': 'Suspicious Discount Pattern',
                    'frequency_anomaly': 'Unusual Invoice Frequency',
                    'vendor_pattern_break': 'Invoice Breaks Vendor Pattern',
                    'cross_vendor_match': 'Matches Invoice from Different Vendor',
                }
                
                title = title_map.get(finding_type, f"Anomaly: {finding_type}")
                
                finding = CrossDocumentFinding.objects.create(
                    extracted_data=extracted_data,
                    organization=extracted_data.organization,
                    finding_type=finding_type,
                    severity=severity,
                    title=title,
                    description=description,
                    confidence_score=max_score,
                    anomaly_score=max_score,
                    analysis_details={
                        'anomaly_type': anomaly_type,
                        'flag_count': len(flags),
                        'flags': [
                            {
                                'description': f.get('description', ''),
                                'score': f.get('score', 0),
                                'context': f.get('context', {}),
                            }
                            for f in flags
                        ],
                    },
                    status='open',
                )
                findings.append(finding)
                logger.info(f"Created {finding_type} finding for {extracted_data.invoice_number}: score={max_score}")
        
        except Exception as e:
            logger.error(f"Error creating anomaly findings: {str(e)}")
        
        return findings
    
    def resolve_finding(self, finding, action, note, resolved_by=None):
        """
        Resolve a finding
        
        Args:
            finding: CrossDocumentFinding instance
            action: 'confirmed', 'dismissed', or 'under_review'
            note: Resolution note
            resolved_by: User who resolved it
        """
        
        try:
            finding.status = action
            finding.is_resolved = action in ['confirmed', 'dismissed']
            finding.resolved_note = note
            finding.resolved_by = resolved_by
            finding.save()
            
            logger.info(f"Finding {finding.id} resolved: {action}")
            
            # Update extracted_data counts
            extracted_data = finding.extracted_data
            extracted_data.cross_document_findings_count = extracted_data.cross_document_findings.count()
            extracted_data.save()
            
            return finding
        
        except Exception as e:
            logger.error(f"Error resolving finding {finding.id}: {str(e)}")
            return None
    
    def get_open_findings(self, extracted_data):
        """Get all open findings for an invoice"""
        return extracted_data.cross_document_findings.filter(status='open')
    
    def get_findings_summary(self, extracted_data):
        """Generate summary of findings for an invoice"""
        
        findings = extracted_data.cross_document_findings.all()
        
        if not findings:
            return "No findings detected"
        
        # Group by type
        by_type = {}
        by_severity = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for finding in findings:
            # Count by type
            ftype = finding.finding_type
            by_type[ftype] = by_type.get(ftype, 0) + 1
            
            # Count by severity
            by_severity[finding.severity] += 1
        
        # Build summary
        parts = []
        
        if by_severity['critical'] > 0:
            parts.append(f"{by_severity['critical']} CRITICAL")
        
        if by_severity['high'] > 0:
            parts.append(f"{by_severity['high']} HIGH")
        
        if by_type.get('potential_duplicate', 0) > 0:
            parts.append(f"potential duplicate")
        
        if by_type.get('unusual_amount', 0) > 0:
            parts.append(f"amount anomaly")
        
        if by_type.get('vat_inconsistency', 0) > 0:
            parts.append(f"VAT issue")
        
        if parts:
            return "Findings: " + ", ".join(parts)
        
        return f"{findings.count()} findings"


# Singleton instance
invoice_cross_document_findings_service = InvoiceCrossDocumentFindingsService()

