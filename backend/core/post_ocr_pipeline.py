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
import json

logger = logging.getLogger(__name__)


def process_ocr_evidence(ocr_evidence):
    """
    Process OCR evidence and create ExtractedData with full pipeline
    """
    try:
        document = ocr_evidence.document
        organization = document.organization
        
        logger.info(f"Processing OCR evidence {ocr_evidence.id} for document {document.id}")
        
        # Get structured data from OCR
        structured = ocr_evidence.structured_data_json or {}
        
        # Helper function to clean date values (convert empty strings to None)
        def clean_date(value):
            if isinstance(value, str) and value.strip() == '':
                return None
            return value
        
        # Helper function to parse string dates to datetime objects
        from datetime import datetime
        def parse_date_to_datetime(value):
            """Convert date string or None to proper datetime object"""
            if not value:
                return None
            if isinstance(value, str):
                if value.strip() == '':
                    return None
                # Try parsing various date formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                # If no format matches, return None
                return None
            # If already a datetime object
            if isinstance(value, datetime):
                return value
            return None
        
        # Save extracted invoice details to OCREvidence
        ocr_evidence.extracted_vendor_name = structured.get('vendor_name', '')
        ocr_evidence.extracted_vendor_address = structured.get('vendor_address', '')
        ocr_evidence.extracted_customer_name = structured.get('customer_name', '')
        ocr_evidence.extracted_customer_address = structured.get('customer_address', '')
        ocr_evidence.extracted_invoice_date = clean_date(structured.get('invoice_date'))
        ocr_evidence.extracted_due_date = clean_date(structured.get('due_date'))
        ocr_evidence.extracted_currency = structured.get('currency', 'SAR')
        ocr_evidence.extracted_items = structured.get('items', [])
        ocr_evidence.save()
        
        # Determine extraction provider from OCR engine
        extraction_provider = 'openai_vision' if 'openai' in ocr_evidence.ocr_engine.lower() else 'tesseract_ocr'
        
        # Get dates from structured JSON and convert to proper datetime objects
        # Use 'issue_date' from structured for invoice_date
        invoice_date = parse_date_to_datetime(structured.get('issue_date'))
        due_date = parse_date_to_datetime(structured.get('due_date'))
        
        # Helper function to convert amounts to Decimal
        from decimal import Decimal
        def to_decimal(value):
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except:
                return None
        
        # Create ExtractedData record
        extracted_data = ExtractedData.objects.create(
            document=document,
            organization=organization,
            # Extracted text
            raw_text_ar=ocr_evidence.text_ar or '',
            raw_text_en=ocr_evidence.text_en or '',
            confidence=ocr_evidence.confidence_score,
            extraction_status='extracted',
            extraction_provider=extraction_provider,
            extraction_completed_at=ocr_evidence.extracted_at,
            # Invoice details
            invoice_number=structured.get('invoice_number') or ocr_evidence.extracted_invoice_number or '',
            vendor_name=ocr_evidence.extracted_vendor_name or structured.get('vendor_name', ''),
            customer_name=ocr_evidence.extracted_customer_name or structured.get('customer_name', ''),
            invoice_date=invoice_date,
            due_date=due_date,
            total_amount=to_decimal(structured.get('total_amount') or ocr_evidence.extracted_total),
            tax_amount=to_decimal(structured.get('tax_amount') or ocr_evidence.extracted_tax),
            currency=ocr_evidence.extracted_currency or structured.get('currency', 'SAR'),
            items_json=ocr_evidence.extracted_items or [],
            # Normalization status
            is_valid=True,
            validation_status='validated',
            normalized_json=structured,
        )
        
        logger.info(f"Created ExtractedData {extracted_data.id} with provider: {extraction_provider}")
        
        # Phase 3: Compliance checks
        try:
            create_compliance_findings(extracted_data, ocr_evidence, organization)
        except Exception as e:
            logger.warning(f"Compliance findings creation failed: {e}")
        
        # Get all findings
        findings = list(AuditFinding.objects.filter(
            related_entity_type='document',
            related_entity_id=extracted_data.document_id
        ))
        
        # Phase 5: Risk scoring
        calculate_risk_score(extracted_data)
        
        # Phase 6: AI Summary (using OpenAI)
        generate_ai_summary(extracted_data, findings)

        # Phase 7: Generate comprehensive audit report (InvoiceAuditReport)
        generate_audit_report(extracted_data, document, organization, ocr_evidence)

        # Save document status
        document.status = 'completed'
        document.save()

        logger.info(f"Successfully processed OCR evidence {ocr_evidence.id}")
        return extracted_data
        
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

