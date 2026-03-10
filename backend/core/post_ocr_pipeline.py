"""
Post-OCR Processing Pipeline
Triggered after OCR evidence is created to extract, normalize, and analyze data
"""
import logging
from documents.models import Document, OCREvidence, ExtractedData
from compliance.models import AuditFinding
from core.models import Organization
from decimal import Decimal
from django.utils import timezone
from django.utils.dateparse import parse_date
import json

logger = logging.getLogger(__name__)


def process_ocr_evidence(ocr_evidence):
    """
    Process OCR evidence and create ExtractedData with full pipeline
    """
    try:
        from documents.services.audit_workflow_service import invoice_audit_workflow_service

        logger.info("Processing OCR evidence %s via canonical audit workflow", ocr_evidence.id)
        return invoice_audit_workflow_service.process_existing_ocr_evidence(
            ocr_evidence=ocr_evidence,
            actor=ocr_evidence.extracted_by,
        )
        
    except Exception as e:
        logger.error(f"Error processing OCR evidence {ocr_evidence.id}: {e}", exc_info=True)
        return None


def create_compliance_findings(extracted_data, ocr_evidence, organization):
    """
    Create compliance findings from extracted data
    """
    try:
        from core.models import User
        import uuid
        from datetime import datetime
        
        # Get system admin user
        system_user = User.objects.filter(role='admin').first() or User.objects.first()
        if not system_user:
            logger.warning("No user available for creating findings")
            return
        
        findings = []
        # Generate unique finding number using timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        finding_base = int(timestamp[-8:])
        
        # VAT validation
        if extracted_data.tax_amount and extracted_data.total_amount:
            if extracted_data.total_amount > 0:
                tax_rate = extracted_data.tax_amount / extracted_data.total_amount
                if tax_rate < Decimal('0.05') or tax_rate > Decimal('0.15'):
                    finding = AuditFinding.objects.create(
                        organization=organization,
                        finding_number=f"FF-{finding_base}-001",
                        finding_type='compliance',
                        risk_level='high',
                        title_ar='معدل ضريبة غير عادي',
                        title_en='Abnormal Tax Rate',
                        description_ar='معدل الضريبة خارج النطاق الطبيعي',
                        description_en='Tax rate outside normal range',
                        impact_ar='قد يشير إلى خطأ في الحساب أو غش',
                        impact_en='May indicate calculation error or fraud',
                        recommendation_ar='مراجعة الفاتورة وتصحيح معدل الضريبة',
                        recommendation_en='Review invoice and correct tax rate',
                        related_entity_type='document',
                        related_entity_id=extracted_data.document_id,
                        identified_by=system_user,
                    )
                    findings.append(finding)
        
        # Vendor validation
        if not extracted_data.vendor_name:
            finding = AuditFinding.objects.create(
                organization=organization,
                finding_number=f"FF-{finding_base}-002",
                finding_type='completeness',
                risk_level='medium',
                title_ar='بائع مفقود',
                title_en='Missing Vendor',
                description_ar='لم يتم استخراج اسم البائع',
                description_en='Vendor name not extracted',
                impact_ar='لا يمكن التحقق من صحة البائع',
                impact_en='Cannot validate vendor',
                recommendation_ar='يجب إدخال اسم البائع يدويا',
                recommendation_en='Vendor name must be entered manually',
                related_entity_type='document',
                related_entity_id=extracted_data.document_id,
                identified_by=system_user,
            )
            findings.append(finding)
        
        # Invoice number validation
        if not extracted_data.invoice_number:
            finding = AuditFinding.objects.create(
                organization=organization,
                finding_number=f"FF-{finding_base}-003",
                finding_type='documentation',
                risk_level='medium',
                title_ar='رقم الفاتورة مفقود',
                title_en='Missing Invoice Number',
                description_ar='لم يتم العثور على رقم الفاتورة',
                description_en='Invoice number not found',
                impact_ar='لا يمكن الربط مع معاملات أخرى',
                impact_en='Cannot link with other transactions',
                recommendation_ar='يجب إدخال رقم الفاتورة يدويا',
                recommendation_en='Invoice number must be entered manually',
                related_entity_type='document',
                related_entity_id=extracted_data.document_id,
                identified_by=system_user,
            )
            findings.append(finding)
        
        # OCR confidence check
        if ocr_evidence.confidence_score < 60:
            finding = AuditFinding.objects.create(
                organization=organization,
                finding_number=f"FF-{finding_base}-004",
                finding_type='accuracy',
                risk_level='low',
                title_ar='ثقة OCR منخفضة',
                title_en='Low OCR Confidence',
                description_ar=f'درجة ثقة OCR منخفضة: {ocr_evidence.confidence_score}%',
                description_en=f'OCR confidence low: {ocr_evidence.confidence_score}%',
                impact_ar='قد تكون البيانات المستخرجة غير دقيقة',
                impact_en='Extracted data may be inaccurate',
                recommendation_ar='يجب مراجعة النتائج يدويا',
                recommendation_en='Results should be manually reviewed',
                related_entity_type='document',
                related_entity_id=extracted_data.document_id,
                identified_by=system_user,
            )
            findings.append(finding)
        
        logger.info(f"Created {len(findings)} compliance findings for {extracted_data.id}")
        
    except Exception as e:
        logger.error(f"Error creating compliance findings: {e}")


def calculate_risk_score(extracted_data):
    """
    Calculate overall risk score for the document
    """
    try:
        risk_score = 0
        
        # Base score from audit findings
        findings = AuditFinding.objects.filter(
            related_entity_type='document',
            related_entity_id=extracted_data.document_id
        )
        
        for finding in findings:
            if finding.risk_level == 'critical':
                risk_score += 40
            elif finding.risk_level == 'high':
                risk_score += 30
            elif finding.risk_level == 'medium':
                risk_score += 15
            elif finding.risk_level == 'low':
                risk_score += 5
        
        # Cap at 100
        risk_score = min(risk_score, 100)
        
        # Save risk score
        extracted_data.risk_score = risk_score
        if risk_score < 20:
            extracted_data.risk_level = 'low'
        elif risk_score < 50:
            extracted_data.risk_level = 'medium'
        elif risk_score < 80:
            extracted_data.risk_level = 'high'
        else:
            extracted_data.risk_level = 'critical'
        extracted_data.save()
        
        logger.info(f"Risk score for {extracted_data.id}: {risk_score} ({extracted_data.risk_level})")
        
    except Exception as e:
        logger.error(f"Error calculating risk score: {e}")


def generate_ai_summary(extracted_data, findings):
    """
    Generate AI-powered audit summary and save to ExtractedData
    """
    try:
        from core.ai_summary_service import ai_summary_service
        
        logger.info(f"Generating AI summary for {extracted_data.id}")
        
        # Call AI service
        summary = ai_summary_service.generate_audit_summary(extracted_data, findings)
        
        # Save to ExtractedData
        extracted_data.audit_summary = summary
        extracted_data.audit_completed_at = timezone.now()
        
        # Save AI explanation in Arabic
        exec_summary = summary.get('executive_summary', '')
        extracted_data.raw_text_ar = exec_summary if exec_summary else extracted_data.raw_text_ar
        
        extracted_data.save()
        
        logger.info(f"AI summary saved for {extracted_data.id}")
        
    except Exception as e:
        logger.error(f"Error generating AI summary: {e}")


def generate_audit_report(extracted_data, document, organization, ocr_evidence):
    """
    Generate comprehensive invoice audit report with all 11 sections
    """
    try:
        from documents.services.audit_report_service import InvoiceAuditReportService
        from core.models import User
        
        logger.info(f"Generating comprehensive audit report for document {document.id}")
        
        # Get current user or system user for the report
        user = getattr(extracted_data, '_current_user', None)
        if not user:
            user = User.objects.filter(role='admin').first() or User.objects.filter(is_staff=True).first()
        
        # Generate comprehensive report with all sections:
        # 1. Document Information
        # 2. Invoice Data Extraction
        # 3. Line Items Details
        # 4. Financial Totals
        # 5. Validation Results
        # 6. Duplicate Detection
        # 7. Anomaly Detection
        # 8. Risk Assessment
        # 9. AI Summary
        # 10. Recommendations
        # 11. Audit Trail
        
        report_service = InvoiceAuditReportService(user=user)
        audit_report = report_service.generate_comprehensive_report(
            extracted_data=extracted_data,
            document=document,
            organization=organization,
            ocr_evidence=ocr_evidence,
        )
        
        logger.info(f"Comprehensive audit report generated: {audit_report.report_number}")
        return audit_report
        
    except Exception as e:
        logger.error(f"Error generating audit report for {document.id}: {e}", exc_info=True)
        return None

