"""
Phase 4: Invoice Cross-Document Intelligence Orchestrator

Orchestrates complete Phase 4 pipeline:
1. Duplicate detection
2. Cross-document validation
3. Anomaly detection
4. Cross-document findings creation
5. Vendor risk calculation
6. Anomaly explanations
7. Audit trail logging

All operations wrapped in atomic transaction for consistency.
"""

import logging
from datetime import datetime
from django.db import transaction

from documents.models import ExtractedData, AuditTrail
from core.invoice_duplicate_detection_service import invoice_duplicate_detection_service
from core.invoice_cross_document_validation_service import invoice_cross_document_validation_service
from core.invoice_anomaly_detection_service import invoice_anomaly_detection_service
from core.invoice_cross_document_findings_service import invoice_cross_document_findings_service
from core.invoice_vendor_risk_service import invoice_vendor_risk_service
from core.invoice_anomaly_explanation_service import invoice_anomaly_explanation_service

logger = logging.getLogger(__name__)


class InvoicePhase4Service:
    """Orchestrator for Phase 4: Cross-Document Intelligence"""
    
    def process_cross_document_intelligence(self, extracted_data):
        """
        Execute complete Phase 4 pipeline
        
        Args:
            extracted_data: ExtractedData instance from Phase 1-3
        
        Returns:
            dict with phase4_result containing all analysis
        """
        
        logger.info(f"Starting Phase 4 for {extracted_data.invoice_number}")
        
        try:
            with transaction.atomic():
                # Initialize result
                phase4_result = {
                    'success': False,
                    'duplicate_analysis': None,
                    'cross_doc_anomalies': None,
                    'anomaly_detection': None,
                    'findings': [],
                    'vendor_risk': None,
                    'explanations': None,
                }
                
                # Step 1: Detect duplicates
                duplicate_matches = invoice_duplicate_detection_service.detect_duplicates(extracted_data)
                if duplicate_matches:
                    extracted_data.duplicate_score = duplicate_matches[0].score
                    extracted_data.duplicate_matched_document = duplicate_matches[0].matched_document if duplicate_matches[0].score >= 60 else None
                    phase4_result['duplicate_analysis'] = {
                        'found': len(duplicate_matches),
                        'best_match_score': duplicate_matches[0].score,
                        'matches': [
                            {
                                'invoice_number': m.matched_document.invoice_number,
                                'score': m.score,
                                'reasons': m.match_reasons[:2],
                            }
                            for m in duplicate_matches[:3]
                        ],
                    }
                    self._create_audit_trail(
                        extracted_data,
                        'duplicate_detection',
                        'Cross-document duplicate detection completed',
                        f'Found {len(duplicate_matches)} potential duplicates (best match: {duplicate_matches[0].score}%)',
                        phase='phase4',
                        success=True,
                    )
                
                # Step 2: Cross-document validation
                cross_doc_anomalies = invoice_cross_document_validation_service.validate_against_history(extracted_data)
                if cross_doc_anomalies:
                    phase4_result['cross_doc_anomalies'] = {
                        'count': len(cross_doc_anomalies),
                        'anomalies': [
                            {
                                'type': a.anomaly_type,
                                'description': a.description,
                                'severity': a.severity,
                                'score': a.score,
                            }
                            for a in cross_doc_anomalies
                        ],
                    }
                
                # Step 3: Composite anomaly detection
                anomaly_detection = invoice_anomaly_detection_service.detect_all_anomalies(
                    extracted_data,
                    duplicate_matches=duplicate_matches,
                    cross_doc_anomalies=cross_doc_anomalies
                )
                
                extracted_data.anomaly_score = anomaly_detection['anomaly_score']
                extracted_data.anomaly_flags = anomaly_detection['anomaly_flags']
                
                phase4_result['anomaly_detection'] = {
                    'anomaly_score': anomaly_detection['anomaly_score'],
                    'total_anomalies': anomaly_detection['total_anomalies'],
                    'has_critical': anomaly_detection['has_critical'],
                    'severity_breakdown': anomaly_detection['severity_breakdown'],
                }
                
                self._create_audit_trail(
                    extracted_data,
                    'anomaly_detection',
                    'Composite anomaly detection completed',
                    f'Anomaly score: {anomaly_detection["anomaly_score"]}, Flags: {anomaly_detection["total_anomalies"]}',
                    phase='phase4',
                    success=True,
                )
                
                # Step 4: Create cross-document findings
                findings = []
                
                # From duplicates
                dup_findings = invoice_cross_document_findings_service.create_findings_from_duplicates(
                    extracted_data,
                    duplicate_matches
                )
                findings.extend(dup_findings)
                
                # From anomalies
                anom_findings = invoice_cross_document_findings_service.create_findings_from_anomalies(
                    extracted_data,
                    anomaly_detection['anomaly_flags']
                )
                findings.extend(anom_findings)
                
                extracted_data.cross_document_findings_count = len(findings)
                
                phase4_result['findings'] = {
                    'created': len(findings),
                    'by_type': {
                        'duplicates': len(dup_findings),
                        'anomalies': len(anom_findings),
                    },
                }
                
                self._create_audit_trail(
                    extracted_data,
                    'findings_created',
                    f'Cross-document findings created',
                    f'Created {len(findings)} findings',
                    phase='phase4',
                    success=True,
                )
                
                # Step 5: Calculate vendor risk
                vendor_risk = invoice_vendor_risk_service.calculate_vendor_risk(extracted_data)
                
                if vendor_risk:
                    extracted_data.vendor_risk_score = vendor_risk.risk_score
                    extracted_data.vendor_risk_level = vendor_risk.risk_level
                    
                    phase4_result['vendor_risk'] = {
                        'vendor_name': vendor_risk.vendor_name,
                        'risk_score': vendor_risk.risk_score,
                        'risk_level': vendor_risk.risk_level,
                        'total_invoices': vendor_risk.total_invoices,
                        'duplicate_count': vendor_risk.duplicate_suspicion_count,
                        'anomaly_count': vendor_risk.anomaly_count,
                        'violation_count': vendor_risk.violation_count,
                    }
                    
                    self._create_audit_trail(
                        extracted_data,
                        'vendor_risk_calculated',
                        'Vendor risk calculated',
                        f'Vendor {vendor_risk.vendor_name}: {vendor_risk.risk_level} ({vendor_risk.risk_score}/100)',
                        phase='phase4',
                        success=True,
                    )
                
                # Step 6: Generate explanations
                explanations = {}
                
                if extracted_data.duplicate_score and extracted_data.duplicate_score >= 60:
                    explanations['duplicate'] = invoice_anomaly_explanation_service.explain_duplicate_suspicion(
                        extracted_data,
                        extracted_data.duplicate_matched_document
                    )
                
                if anomaly_detection['anomaly_flags']:
                    explanations['anomalies'] = invoice_anomaly_explanation_service.explain_anomalies(
                        extracted_data,
                        anomaly_detection['anomaly_flags']
                    )
                
                if vendor_risk:
                    explanations['vendor_risk'] = invoice_anomaly_explanation_service.explain_vendor_risk(vendor_risk)
                
                explanations['recommendation'] = invoice_anomaly_explanation_service.generate_reviewer_recommendation(
                    extracted_data
                )
                
                phase4_result['explanations'] = explanations
                
                self._create_audit_trail(
                    extracted_data,
                    'explanations_generated',
                    'AI explanations generated',
                    f'Generated {len(explanations)} explanations',
                    phase='phase4',
                    success=True,
                )
                
                # Step 7: Save extracted data with Phase 4 results
                extracted_data.phase4_completed_at = datetime.now()
                extracted_data.save()
                
                phase4_result['success'] = True
                
                logger.info(f"Phase 4 completed for {extracted_data.invoice_number}: {phase4_result}")
                
                return phase4_result
        
        except Exception as e:
            logger.error(f"Error in Phase 4 for {extracted_data.id}: {str(e)}")
            
            # Log error
            try:
                self._create_audit_trail(
                    extracted_data,
                    'phase4_error',
                    'Phase 4 processing error',
                    f'Error: {str(e)}',
                    phase='phase4',
                    success=False,
                )
            except:
                pass
            
            # Return error result
            return {
                'success': False,
                'error': str(e),
                'duplicate_analysis': None,
                'cross_doc_anomalies': None,
                'anomaly_detection': None,
                'findings': [],
                'vendor_risk': None,
                'explanations': None,
            }
    
    def _create_audit_trail(self, extracted_data, event_type, title, description, phase=None, success=True):
        """Create audit trail entry"""
        try:
            AuditTrail.objects.create(
                extracted_data=extracted_data,
                organization=extracted_data.organization,
                event_type=event_type,
                severity='info' if success else 'error',
                title=title,
                description=description,
                success=success,
                phase=phase,
            )
        except Exception as e:
            logger.warning(f"Error creating audit trail: {str(e)}")


# Singleton instance
invoice_phase4_service = InvoicePhase4Service()

