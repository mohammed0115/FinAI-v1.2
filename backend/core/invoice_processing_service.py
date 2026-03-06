"""
Invoice Processing Service - Phase 2 Integration

Orchestrates:
1. Normalization of extracted data
2. Validation
3. Saving results to database
4. Creating audit findings
5. Mapping to financial objects
"""

import logging
from decimal import Decimal
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


def process_extracted_invoice(
    extracted_data_obj: 'ExtractedData',
    raw_extracted_json: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process extracted invoice through complete pipeline
    
    Phase 2: Normalization and Validation
    Phase 3: Compliance checks, Risk scoring, Audit summary
    Phase 4: Cross-document intelligence, Vendor risk, Findings
    
    Args:
        extracted_data_obj: ExtractedData database object
        raw_extracted_json: Raw JSON from OpenAI Vision or OCR
        
    Returns:
        Dict with processing results across all phases
    """
    from core.invoice_normalization_service import invoice_normalization_service
    from core.invoice_validation_service import invoice_validation_service, get_validation_summary
    from core.invoice_phase3_service import invoice_phase3_service
    from documents.models import InvoiceAuditFinding, AuditTrail
    
    result = {
        'success': False,
        'normalized_data': None,
        'is_valid': False,
        'validation_summary': None,
        'risk_score': 0,
        'risk_level': 'Low',
        'audit_summary': None,
        'audit_findings_created': 0,
        'phase4_success': False,
        'duplicate_analysis': None,
        'anomaly_detection': None,
        'vendor_risk': None,
        'cross_document_findings': None,
        'explanations': None,
        'phase5_success': False,
        'phase5_result': None,
        'error': None
    }
    
    try:
        # PHASE 2: Normalize and Validate
        logger.info(f"Starting Phase 2 processing for {extracted_data_obj.id}")
        
        # Step 1: Normalize the extracted data
        logger.info(f"Normalizing invoice data for {extracted_data_obj.id}")
        normalized_data = invoice_normalization_service.normalize_invoice_json(raw_extracted_json)
        result['normalized_data'] = normalized_data
        
        # Create audit trail for normalization
        _create_audit_trail(
            extracted_data_obj=extracted_data_obj,
            event_type='normalization',
            title='Invoice data normalized',
            phase='phase2'
        )
        
        # Step 2: Validate the normalized data
        logger.info(f"Validating invoice data for {extracted_data_obj.id}")
        is_valid, validation_messages = invoice_validation_service.validate_invoice(normalized_data)
        validation_summary = get_validation_summary(validation_messages)
        
        result['is_valid'] = is_valid
        result['validation_summary'] = validation_summary
        
        # Create audit trail for validation
        _create_audit_trail(
            extracted_data_obj=extracted_data_obj,
            event_type='validation',
            title=f'Invoice validation completed',
            result_summary=f"Valid: {is_valid}, Errors: {len(validation_summary['errors'])}, Warnings: {len(validation_summary['warnings'])}",
            phase='phase2'
        )
        
        # Step 3: Save Phase 2 results
        logger.info(f"Saving Phase 2 results for {extracted_data_obj.id}")
        with transaction.atomic():
            extracted_data_obj.normalized_json = normalized_data
            extracted_data_obj.is_valid = is_valid
            extracted_data_obj.validation_errors = validation_summary['errors']
            extracted_data_obj.validation_warnings = validation_summary['warnings']
            extracted_data_obj.validation_completed_at = timezone.now()
            extracted_data_obj.extraction_completed_at = timezone.now()  # Mark extraction complete
            extracted_data_obj.extraction_status = 'extracted'
            extracted_data_obj.save()
            
            # Step 4: Create audit findings from Phase 2 validation
            audit_findings_created = _create_audit_findings(
                extracted_data_obj,
                validation_messages,
                normalized_data
            )
            result['audit_findings_created'] = audit_findings_created
            logger.info(f"Created {audit_findings_created} audit findings for {extracted_data_obj.id}")
        
        # PHASE 3: Compliance, Risk Scoring, Audit Summary
        logger.info(f"Starting Phase 3 processing for {extracted_data_obj.id}")
        
        phase3_result = invoice_phase3_service.process_compliance_and_audit(
            extracted_data_obj=extracted_data_obj,
            extracted_json=raw_extracted_json,
            normalized_json=normalized_data,
            validation_errors=validation_summary['errors'],
            validation_warnings=validation_summary['warnings']
        )
        
        result['risk_score'] = phase3_result['risk_score']
        result['risk_level'] = phase3_result['risk_level']
        result['audit_summary'] = phase3_result['audit_summary']
        result['audit_findings_created'] += phase3_result['audit_finding_count']
        
        # PHASE 4: Cross-Document Intelligence & Vendor Risk
        logger.info(f"Starting Phase 4 processing for {extracted_data_obj.id}")
        
        from core.invoice_phase4_service import invoice_phase4_service
        
        phase4_result = invoice_phase4_service.process_cross_document_intelligence(
            extracted_data_obj=extracted_data_obj
        )
        
        result['phase4_success'] = phase4_result['success']
        result['duplicate_analysis'] = phase4_result['duplicate_analysis']
        result['anomaly_detection'] = phase4_result['anomaly_detection']
        result['vendor_risk'] = phase4_result['vendor_risk']
        result['cross_document_findings'] = phase4_result['findings']
        result['explanations'] = phase4_result['explanations']
        result['audit_findings_created'] += phase4_result['findings'].get('created', 0)
        
        # PHASE 5: Financial Intelligence & Forecasting
        logger.info(f"Starting Phase 5 processing for {extracted_data_obj.id}")
        
        try:
            from core.invoice_phase5_service import get_phase5_service
            
            phase5_service = get_phase5_service()
            phase5_result = phase5_service.process_phase5(
                extracted_data=extracted_data_obj,
                organization=extracted_data_obj.organization
            )
            
            result['phase5_success'] = phase5_result['success']
            result['phase5_result'] = phase5_result
        except Exception as e:
            logger.warning(f"Phase 5 processing encountered error: {str(e)}")
            result['phase5_success'] = False
            result['phase5_result'] = {
                'success': False,
                'error': str(e)
            }
        
        # Step 5: Try to map to financial objects
        _create_financial_objects(extracted_data_obj, normalized_data, validation_messages)
        
        result['success'] = True
        logger.info(f"Successfully processed invoice {extracted_data_obj.id} through all phases")
        
        return result
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error processing invoice {extracted_data_obj.id}: {e}", exc_info=True)
        
        # Mark extraction as failed
        try:
            extracted_data_obj.extraction_status = 'failed'
            extracted_data_obj.extraction_error = str(e)
            extracted_data_obj.save()
            
            _create_audit_trail(
                extracted_data_obj=extracted_data_obj,
                event_type='extraction',
                title='Invoice processing failed',
                description=str(e),
                severity='error',
                success=False,
                phase='phase3'
            )
        except:
            pass
        
        return result


def _create_audit_findings(
    extracted_data_obj: 'ExtractedData',
    validation_messages: List,
    normalized_data: Dict[str, Any]
) -> int:
    """
    Create InvoiceAuditFinding records for validation issues
    
    Args:
        extracted_data_obj: ExtractedData instance
        validation_messages: List of ValidationMessage objects
        normalized_data: Normalized invoice data
        
    Returns:
        Number of findings created
    """
    from documents.models import InvoiceAuditFinding
    
    findings_count = 0
    
    for message in validation_messages:
        # Only create findings for errors, not warnings
        if message.level != 'error':
            continue
        
        try:
            finding = InvoiceAuditFinding.objects.create(
                extracted_data=extracted_data_obj,
                organization=extracted_data_obj.organization,
                finding_type='missing_field' if 'MISSING' in message.code else 'other',
                severity='high' if 'MISSING' in message.code else 'medium',
                description=message.message,
                field=message.field
            )
            findings_count += 1
            logger.debug(f"Created audit finding: {finding.id}")
        except Exception as e:
            logger.error(f"Error creating audit finding: {e}", exc_info=True)
    
    # Create finding for total mismatch if detected
    if any(m.code == 'TOTAL_MISMATCH' for m in validation_messages):
        calculated_total = _calculate_line_totals(normalized_data.get('items', []))
        invoice_total = _parse_decimal(normalized_data.get('total_amount'))
        
        if calculated_total is not None and invoice_total is not None:
            difference = abs(calculated_total - invoice_total)
            
            try:
                finding = InvoiceAuditFinding.objects.create(
                    extracted_data=extracted_data_obj,
                    organization=extracted_data_obj.organization,
                    finding_type='total_mismatch',
                    severity='critical',
                    description=f'Sum of line totals ({calculated_total}) does not match invoice total ({invoice_total})',
                    field='total_amount',
                    expected_value=str(calculated_total),
                    actual_value=str(invoice_total),
                    difference=difference
                )
                findings_count += 1
                logger.warning(f"Created total mismatch finding: {finding.id}, difference: {difference}")
            except Exception as e:
                logger.error(f"Error creating total mismatch finding: {e}", exc_info=True)
    
    return findings_count


def _create_financial_objects(
    extracted_data_obj: 'ExtractedData',
    normalized_data: Dict[str, Any],
    validation_messages: List
) -> None:
    """
    Create financial objects (journal entries, transactions, etc.) from extracted invoice
    
    Args:
        extracted_data_obj: ExtractedData instance
        normalized_data: Normalized invoice data
        validation_messages: List of validation messages
    """
    # Only create financial objects if validation passed
    has_errors = any(m.level == 'error' for m in validation_messages)
    if has_errors:
        logger.info(f"Skipping financial object creation for invalid invoice {extracted_data_obj.id}")
        return
    
    # TODO: Implementation in Phase 3
    # - Create Transaction record
    # - Create JournalEntry draft
    # - Flag VAT transactions
    # - Create AuditFlag for discrepancies
    logger.info(f"Financial object creation deferred for {extracted_data_obj.id} (Phase 3)")


def _calculate_line_totals(items: List[Dict]) -> Optional[Decimal]:
    """Calculate sum of line item totals"""
    total = Decimal('0')
    
    for item in items:
        item_total = _parse_decimal(item.get('total'))
        if item_total is not None:
            total += item_total
    
    return total if total > 0 else None


def _parse_decimal(value: Any) -> Optional[Decimal]:
    """Parse value to Decimal"""
    if value is None:
        return None
    
    try:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            return Decimal(value)
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        return None
    except:
        return None


def _create_audit_trail(
    extracted_data_obj: 'ExtractedData',
    event_type: str,
    title: str,
    description: str = None,
    result_summary: str = None,
    severity: str = 'info',
    success: bool = True,
    phase: str = None
) -> None:
    """
    Create an audit trail entry for this event.
    
    Args:
        extracted_data_obj: ExtractedData instance
        event_type: Type of event (extraction, normalization, validation, etc.)
        title: Event title
        description: Event details
        result_summary: Summary of operation result
        severity: Severity level (info, warning, error, critical)
        success: Did the operation succeed?
        phase: Phase (phase1, phase2, phase3)
    """
    from documents.models import AuditTrail
    
    try:
        AuditTrail.objects.create(
            extracted_data=extracted_data_obj,
            organization=extracted_data_obj.organization,
            event_type=event_type,
            title=title,
            description=description,
            severity=severity,
            success=success,
            result_summary=result_summary,
            phase=phase
        )
        logger.debug(f"Created audit trail: {event_type}")
    except Exception as e:
        logger.error(f"Failed to create audit trail: {str(e)}")
