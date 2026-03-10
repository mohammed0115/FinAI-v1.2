"""
Django signals for automatic processing
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from documents.domain_signals import invoice_persisted
from documents.models import AuditSession, OCREvidence, ExtractedData
import logging

logger = logging.getLogger(__name__)


@receiver(invoice_persisted)
def trigger_initial_invoice_audit(sender, invoice, extracted_data, actor=None, **kwargs):
    """Start the deterministic ingestion audit procedures after persistence."""
    try:
        from documents.services.ingestion_audit_service import invoice_ingestion_audit_service

        return invoice_ingestion_audit_service.run_initial_checks(
            invoice=invoice,
            extracted_data=extracted_data,
            actor=actor,
        )
    except Exception as exc:
        logger.error("Error while running ingestion audit procedures: %s", exc, exc_info=True)
        return None


@receiver(post_save, sender=OCREvidence)
def trigger_post_ocr_pipeline(sender, instance, created, **kwargs):
    """
    Automatically trigger post-OCR pipeline when OCREvidence is created
    """
    if not created:
        return

    if AuditSession.objects.filter(document=instance.document, status='processing').exists():
        logger.info("Skipping OCREvidence signal for document %s because a canonical audit session is running", instance.document_id)
        return
    
    try:
        from core.post_ocr_pipeline import process_ocr_evidence
        logger.info(f"Signal triggered for OCREvidence {instance.id}")
        extracted_data = process_ocr_evidence(instance)
        if extracted_data:
            logger.info(f"Post-OCR pipeline auto-triggered for {instance.document_id}")
    except Exception as e:
        logger.warning(f"Signal handler error: {e}")


@receiver(post_save, sender=ExtractedData)
def auto_generate_audit_report(sender, instance: ExtractedData, created: bool, **kwargs):
    """
    Automatically generate an audit report when ExtractedData is created.
    
    This signal triggers the comprehensive audit report generation pipeline
    whenever invoice data is extracted or updated.
    """
    
    if not created:
        # Only generate on creation, not on updates
        return

    if AuditSession.objects.filter(document=instance.document, status='processing').exists():
        logger.info("Skipping auto report generation for document %s because a canonical audit session is running", instance.document_id)
        return
    
    try:
        # Skip if report already exists
        if hasattr(instance, 'audit_report') and instance.audit_report:
            logger.info(f"Audit report already exists for ExtractedData {instance.id}")
            return
        
        # Get related document
        document = instance.document
        organization = instance.organization
        
        # Get OCR evidence if it exists
        ocr_evidence = document.ocr_evidence_records.first()
        
        # Generate the comprehensive audit report
        from documents.services import InvoiceAuditReportService
        
        service = InvoiceAuditReportService(user=document.uploaded_by)
        report = service.generate_comprehensive_report(
            extracted_data=instance,
            document=document,
            organization=organization,
            ocr_evidence=ocr_evidence
        )
        
        logger.info(
            f"Audit report generated successfully: {report.report_number} "
            f"for document {document.id}"
        )
        
        # Update document status if needed
        if document.status not in ['validated', 'completed']:
            document.status = 'completed'
            document.processed_at = timezone.now()
            document.save()
        
    except Exception as e:
        logger.error(
            f"Error in auto_generate_audit_report for ExtractedData {instance.id}: {e}",
            exc_info=True
        )
