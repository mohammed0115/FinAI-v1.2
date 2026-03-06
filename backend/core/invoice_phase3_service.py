# Phase 3: Invoice Compliance, Risk Scoring & Audit Summary Service
# Orchestrates Phase 3 workflow: compliance checks -> risk scoring -> audit summary
# Called automatically after Phase 2 (normalization & validation)

import logging
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from core.invoice_compliance_service import invoice_compliance_service
from core.invoice_risk_scoring_service import invoice_risk_scoring_service
from core.invoice_audit_summary_service import invoice_audit_summary_service

logger = logging.getLogger(__name__)


class InvoicePhase3Service:
    """
    Orchestrate Phase 3 of invoice processing pipeline:
    1. Run compliance checks
    2. Compute risk score
    3. Generate audit summary
    4. Create audit trail
    5. Create findings from critical issues
    """
    
    def process_compliance_and_audit(
        self,
        extracted_data,
        extracted_json: dict,
        normalized_json: dict,
        validation_errors: list,
        validation_warnings: list
    ) -> dict:
        """
        Execute complete Phase 3 workflow on invoice.
        
        Returns dict with:
        - compliance_checks (list)
        - risk_score (int, 0-100)
        - risk_level (str)
        - audit_summary (dict)
        - audit_finding_count (int)
        - success (bool)
        """
        
        try:
            with transaction.atomic():
                # Step 1: Run compliance checks
                logger.info(f"Starting Phase 3 for ExtractedData {extracted_data.id}")
                
                compliance_checks, all_critical_pass = invoice_compliance_service.check_invoice_compliance(
                    normalized_json
                )
                logger.info(f"Completed {len(compliance_checks)} compliance checks")
                
                # Convert to dicts for storage
                compliance_check_dicts = [c.to_dict() for c in compliance_checks]
                
                # Step 2: Compute risk score
                risk_score, risk_level = invoice_risk_scoring_service.compute_risk_score(compliance_checks)
                logger.info(f"Risk score: {risk_score}/100, Level: {risk_level}")
                
                # Step 3: Generate audit summary (OpenAI or rule-based)
                audit_summary = invoice_audit_summary_service.generate_audit_summary(
                    extracted_json=extracted_json,
                    normalized_json=normalized_json,
                    validation_errors=validation_errors,
                    validation_warnings=validation_warnings,
                    compliance_checks=compliance_check_dicts,
                    risk_score=risk_score,
                    risk_level=risk_level
                )
                logger.info(f"Generated audit summary, status: {audit_summary.get('final_status')}")
                
                # Step 4: Save Phase 3 results to ExtractedData
                extracted_data.compliance_checks = compliance_check_dicts
                extracted_data.risk_score = risk_score
                extracted_data.risk_level = risk_level
                extracted_data.audit_summary = audit_summary
                extracted_data.audit_completed_at = timezone.now()
                extracted_data.save()
                logger.info(f"Saved Phase 3 results to ExtractedData")
                
                # Step 5: Create AuditTrail entry
                self._create_audit_trail_entry(
                    extracted_data=extracted_data,
                    event_type='audit_summary',
                    title='Compliance checks, risk scoring, and audit summary completed',
                    result_summary=f"Risk Level: {risk_level}, Score: {risk_score}/100",
                    phase='phase3'
                )
                
                # Step 6: Create audit findings from critical compliance failures
                finding_count = self._create_findings_from_compliance_checks(
                    extracted_data=extracted_data,
                    compliance_checks=compliance_checks
                )
                logger.info(f"Created {finding_count} audit findings from compliance checks")
                
                return {
                    "compliance_checks": compliance_check_dicts,
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "audit_summary": audit_summary,
                    "audit_finding_count": finding_count,
                    "success": True,
                    "all_critical_pass": all_critical_pass
                }
        
        except Exception as e:
            logger.error(f"Phase 3 processing failed: {str(e)}", exc_info=True)
            
            # Create error audit trail entry
            self._create_audit_trail_entry(
                extracted_data=extracted_data,
                event_type='compliance_check',
                title='Phase 3 processing failed',
                description=str(e),
                severity='error',
                success=False,
                phase='phase3'
            )
            
            raise
    
    def _create_findings_from_compliance_checks(self, extracted_data, compliance_checks: list) -> int:
        """
        Create InvoiceAuditFinding records for failed/critical compliance checks.
        
        Returns: number of findings created
        """
        from documents.models import InvoiceAuditFinding
        
        finding_count = 0
        
        # Map compliance check to finding type
        check_to_finding_type = {
            'invoice_number': 'missing_field',
            'vendor_presence': 'missing_field',
            'customer_presence': 'missing_field',
            'items_existence': 'missing_field',
            'total_consistency': 'total_mismatch',
            'vat_tin_check': 'vat_flag',
            'due_date_logic': 'date_mismatch',
            'currency_validity': 'invalid_value',
            'suspicious_discount': 'other',
        }
        
        # Map severity
        severity_map = {
            'INFO': 'low',
            'WARNING': 'medium',
            'ERROR': 'high',
            'CRITICAL': 'critical'
        }
        
        for check in compliance_checks:
            # Only create findings for failures
            if check.status == 'PASS':
                continue
            
            finding_type = check_to_finding_type.get(check.check_name, 'other')
            severity = severity_map.get(check.severity, 'medium')
            
            try:
                finding = InvoiceAuditFinding.objects.create(
                    extracted_data=extracted_data,
                    organization=extracted_data.organization,
                    finding_type=finding_type,
                    severity=severity,
                    description=check.message,
                    field=None,  # Not always applicable
                    expected_value=None,
                    actual_value=None,
                    difference=None,
                    is_resolved=False
                )
                finding_count += 1
                logger.debug(f"Created finding: {finding.id} from check {check.check_name}")
            
            except Exception as e:
                logger.error(f"Failed to create finding from check {check.check_name}: {str(e)}")
        
        return finding_count
    
    def _create_audit_trail_entry(
        self,
        extracted_data,
        event_type: str,
        title: str,
        description: str = None,
        result_summary: str = None,
        severity: str = 'info',
        success: bool = True,
        phase: str = None,
        duration_ms: int = None,
        details: dict = None,
        performed_by = None
    ) -> None:
        """Create an audit trail entry for this event."""
        from documents.models import AuditTrail
        
        try:
            AuditTrail.objects.create(
                extracted_data=extracted_data,
                organization=extracted_data.organization,
                event_type=event_type,
                title=title,
                description=description,
                severity=severity,
                success=success,
                result_summary=result_summary,
                phase=phase,
                duration_ms=duration_ms,
                details=details,
                performed_by=performed_by
            )
            logger.debug(f"Created audit trail: {event_type}")
        except Exception as e:
            logger.error(f"Failed to create audit trail: {str(e)}")


# Singleton instance
invoice_phase3_service = InvoicePhase3Service()
