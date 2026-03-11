"""
Financial Audit Report Generation Service

Handles all aspects of invoice audit report generation including:
- Data validation and verification
- Duplicate detection
- Anomaly detection
- Risk scoring
- AI-powered analysis and recommendations
- Report compilation and storage
"""

import json
import uuid
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from django.utils import timezone
from documents.models import (
    InvoiceAuditReport, ExtractedData, Document, 
    OCREvidence, InvoiceAuditFinding, AuditTrail, CrossDocumentFinding
)
from core.models import User, Organization
import logging
from django.db.models import Q, Count, Sum
from .openai_service import OpenAIService
from documents.report_presenter import build_report_presentation

logger = logging.getLogger(__name__)


class DataValidationService:
    """Validates invoice data and generates validation results"""
    
    @staticmethod
    def validate_invoice_number(invoice_number: str) -> Dict[str, Any]:
        """Validate invoice number format and uniqueness"""
        result = {'status': 'pass', 'issues': []}
        
        if not invoice_number or invoice_number.strip() == '':
            result['status'] = 'fail'
            result['issues'].append('Invoice number is missing')
        elif len(invoice_number.strip()) < 3:
            result['status'] = 'warning'
            result['issues'].append('Invoice number is unusually short')
            
        return result
    
    @staticmethod
    def validate_vendor(vendor_name: str, vendor_tin: Optional[str] = None) -> Dict[str, Any]:
        """Validate vendor information"""
        result = {'status': 'pass', 'issues': []}
        
        if not vendor_name or vendor_name.strip() == '':
            result['status'] = 'fail'
            result['issues'].append('Vendor name is missing')
        
        if vendor_tin and len(vendor_tin.strip()) > 0:
            # TIN validation (basic format check)
            if len(vendor_tin.strip()) < 5:
                result['status'] = 'warning'
                result['issues'].append('Vendor TIN appears to be invalid format')
        else:
            result['status'] = 'warning'
            result['issues'].append('Vendor TIN is missing')
        
        return result
    
    @staticmethod
    def validate_customer(customer_name: str, customer_tin: Optional[str] = None) -> Dict[str, Any]:
        """Validate customer information"""
        result = {'status': 'pass', 'issues': []}
        
        if not customer_name or customer_name.strip() == '':
            result['status'] = 'fail'
            result['issues'].append('Customer name is missing')
        
        if customer_tin and len(customer_tin.strip()) > 0:
            # TIN validation (basic format check)
            if len(customer_tin.strip()) < 5:
                result['status'] = 'warning'
                result['issues'].append('Customer TIN appears to be invalid format')
        else:
            result['status'] = 'warning'
            result['issues'].append('Customer TIN is missing')
        
        return result
    
    @staticmethod
    def validate_line_items(items: List[Dict]) -> Dict[str, Any]:
        """Validate line items structure and calculations"""
        result = {'status': 'pass', 'issues': []}
        
        if not items or len(items) == 0:
            result['status'] = 'fail'
            result['issues'].append('No line items found on invoice')
            return result
        
        total_calculated = Decimal('0')
        
        for idx, item in enumerate(items, 1):
            try:
                qty = Decimal(str(item.get('quantity', 0)))
                unit_price = Decimal(str(item.get('unit_price', 0)))
                discount = Decimal(str(item.get('discount', 0)))
                total = Decimal(str(item.get('total', 0)))
                
                expected_total = (qty * unit_price) - discount
                
                if expected_total != total:
                    result['status'] = 'warning'
                    result['issues'].append(
                        f"Line {idx}: Calculated total ({expected_total}) "
                        f"does not match stated total ({total})"
                    )
                
                total_calculated += total
            except (ValueError, TypeError) as e:
                result['status'] = 'warning'
                result['issues'].append(f"Line {idx}: Invalid numeric value - {str(e)}")
        
        return result
    
    @staticmethod
    def validate_total_match(
        line_items: List[Dict],
        subtotal: Optional[Decimal],
        vat: Optional[Decimal],
        total: Optional[Decimal]
    ) -> Dict[str, Any]:
        """Validate that totals match line items"""
        result = {'status': 'pass', 'issues': []}
        
        try:
            if not line_items or len(line_items) == 0:
                result['status'] = 'fail'
                result['issues'].append('Cannot verify totals without line items')
                return result
            
            calculated_subtotal = Decimal('0')
            for item in line_items:
                calculated_subtotal += Decimal(str(item.get('total', 0)))
            
            # Check subtotal
            if subtotal:
                if Decimal(str(subtotal)) != calculated_subtotal:
                    result['status'] = 'warning'
                    result['issues'].append(
                        f"Subtotal mismatch: Calculated {calculated_subtotal}, "
                        f"but invoice shows {subtotal}"
                    )
            
            # Check total
            if total:
                expected_total = calculated_subtotal
                if vat:
                    expected_total += Decimal(str(vat))
                
                if Decimal(str(total)) != expected_total:
                    result['status'] = 'warning'
                    result['issues'].append(
                        f"Total mismatch: Calculated {expected_total}, "
                        f"but invoice shows {total}"
                    )
        except (ValueError, TypeError) as e:
            result['status'] = 'warning'
            result['issues'].append(f"Error calculating totals: {str(e)}")
        
        return result
    
    @staticmethod
    def validate_vat(vat_amount: Optional[Decimal], total_amount: Optional[Decimal]) -> Dict[str, Any]:
        """Validate VAT correctness"""
        result = {'status': 'pass', 'issues': []}
        
        if not vat_amount or vat_amount == 0:
            result['status'] = 'warning'
            result['issues'].append('VAT amount is missing or zero')
            return result
        
        # Check if VAT is reasonable (typically 5-15%)
        if total_amount and total_amount > 0:
            vat_rate = (Decimal(str(vat_amount)) / Decimal(str(total_amount))) * 100
            if vat_rate < 1 or vat_rate > 30:  # Reasonable VAT range
                result['status'] = 'warning'
                result['issues'].append(
                    f"VAT rate appears unusual: {vat_rate:.2f}% "
                    f"(typically 5-15%)"
                )
        
        return result
    
    @classmethod
    def validate_all(cls, extracted_data: ExtractedData) -> Dict[str, Any]:
        """Run all validation checks and compile results"""
        validation_results = {
            'invoice_number': cls.validate_invoice_number(extracted_data.invoice_number),
            'vendor': cls.validate_vendor(
                extracted_data.vendor_name,
                extracted_data.vendor_tax_id,
            ),
            'customer': cls.validate_customer(
                extracted_data.customer_name,
                extracted_data.customer_tax_id,
            ),
            'items': cls.validate_line_items(extracted_data.items_json or []),
            'total_match': cls.validate_total_match(
                extracted_data.items_json or [],
                extracted_data.total_amount,
                extracted_data.tax_amount,
                extracted_data.total_amount
            ),
            'vat': cls.validate_vat(extracted_data.tax_amount, extracted_data.total_amount),
        }
        
        return validation_results


class DuplicateDetectionService:
    """Detects potential duplicate invoices"""
    
    @staticmethod
    def calculate_duplicate_score(
        extracted_data: ExtractedData,
        organization: Organization
    ) -> Tuple[int, List[int], str]:
        """
        Calculate probability that this is a duplicate invoice.
        Returns: (score 0-100, list of matched document IDs, status)
        """
        score = 0
        matched_docs = []
        
        # Search for similar invoices in the same organization
        similar_invoices = ExtractedData.objects.filter(
            organization=organization,
            vendor_name=extracted_data.vendor_name,
        ).exclude(id=extracted_data.id)
        
        # Exact match checks
        if extracted_data.invoice_number:
            exact_match = similar_invoices.filter(
                invoice_number=extracted_data.invoice_number,
                total_amount=extracted_data.total_amount
            ).first()
            
            if exact_match:
                score += 100
                matched_docs.append(str(exact_match.id))
        
        # High similarity checks
        high_similarity = similar_invoices.filter(
            total_amount=extracted_data.total_amount,
            vendor_name=extracted_data.vendor_name
        )
        
        # Only filter by date if available
        if extracted_data.invoice_date:
            high_similarity = high_similarity.filter(
                invoice_date=extracted_data.invoice_date
            )
        
        for doc in high_similarity[:3]:  # Check up to 3 matches
            if score < 100:
                score += 30
                matched_docs.append(str(doc.id))
        
        # Amount similarity within 1%
        if extracted_data.total_amount:
            threshold = Decimal(str(extracted_data.total_amount)) * Decimal('0.01')
            amount_similar = similar_invoices.filter(
                total_amount__gte=extracted_data.total_amount - threshold,
                total_amount__lte=extracted_data.total_amount + threshold,
            )
            
            # Only filter by month/year if date is available and is a proper datetime
            if extracted_data.invoice_date and hasattr(extracted_data.invoice_date, 'month'):
                try:
                    amount_similar = amount_similar.filter(
                        invoice_date__month=extracted_data.invoice_date.month,
                        invoice_date__year=extracted_data.invoice_date.year
                    )
                except (AttributeError, TypeError):
                    # If date is not a proper datetime, skip the filter
                    pass
            
            for doc in amount_similar[:2]:
                if score < 100:
                    score += 15
        
        # Determine status
        if score >= 80:
            status = 'confirmed_duplicate'
        elif score >= 50:
            status = 'high_risk'
        elif score >= 20:
            status = 'medium_risk'
        elif score > 0:
            status = 'low_risk'
        else:
            status = 'no_duplicate'
        
        return min(score, 100), matched_docs, status


class AnomalyDetectionService:
    """Detects unusual patterns in invoices"""
    
    @staticmethod
    def detect_amount_anomalies(
        extracted_data: ExtractedData,
        organization: Organization
    ) -> Tuple[List[str], int]:
        """Detect unusual invoice amounts"""
        from decimal import Decimal
        
        anomalies = []
        score = 0
        
        if not extracted_data.total_amount:
            return anomalies, score
        
        # Get vendor statistics
        vendor_invoices = ExtractedData.objects.filter(
            organization=organization,
            vendor_name=extracted_data.vendor_name
        ).exclude(id=extracted_data.id)
        
        if vendor_invoices.count() < 3:
            return anomalies, score  # Not enough data
        
        # Calculate average and std deviation
        vendor_amounts = vendor_invoices.filter(
            total_amount__isnull=False
        ).values_list('total_amount', flat=True)
        
        if len(vendor_amounts) > 0:
            avg = sum(vendor_amounts) / len(vendor_amounts)
            
            # Convert to Decimal for consistent type operations
            avg_decimal = Decimal(str(avg)) if not isinstance(avg, Decimal) else avg
            total_amount = Decimal(str(extracted_data.total_amount)) if not isinstance(extracted_data.total_amount, Decimal) else extracted_data.total_amount
            
            # Check if amount is more than 3x the average
            if total_amount > avg_decimal * Decimal('3'):
                anomalies.append(f"Invoice amount ({total_amount}) is 3x higher than average from this vendor ({avg_decimal})")
                score += 30
            elif total_amount < avg_decimal * Decimal('0.3'):
                anomalies.append(f"Invoice amount ({total_amount}) is significantly lower than average from this vendor ({avg_decimal})")
                score += 20
        
        return anomalies, score
    
    @staticmethod
    def detect_date_anomalies(
        extracted_data: ExtractedData,
        organization: Organization
    ) -> Tuple[List[str], int]:
        """Detect unusual date patterns"""
        anomalies = []
        score = 0
        
        if not extracted_data.invoice_date or not extracted_data.due_date:
            return anomalies, score
        
        # Check if due date is before issue date
        if extracted_data.due_date < extracted_data.invoice_date:
            anomalies.append("Due date is before invoice date")
            score += 25
        
        # Check if payment terms are unusual (more than 120 days)
        days_to_pay = (extracted_data.due_date - extracted_data.invoice_date).days
        if days_to_pay > 120:
            anomalies.append(f"Unusual payment terms: {days_to_pay} days")
            score += 15
        elif days_to_pay < 0:
            anomalies.append("Due date is in the past")
            score += 30
        
        return anomalies, score
    
    @staticmethod
    def detect_format_anomalies(
        extracted_data: ExtractedData,
        ocr_evidence: Optional[OCREvidence] = None
    ) -> Tuple[List[str], int]:
        """Detect anomalies in document format"""
        anomalies = []
        score = 0
        
        if ocr_evidence and ocr_evidence.confidence_score < 60:
            anomalies.append(f"Low OCR confidence: {ocr_evidence.confidence_score}%")
            score += 20
        
        # Check if items_json is missing or malformed
        if not extracted_data.items_json or len(extracted_data.items_json) == 0:
            anomalies.append("No line items extracted from invoice")
            score += 25
        
        return anomalies, score
    
    @classmethod
    def calculate_anomaly_score(
        cls,
        extracted_data: ExtractedData,
        organization: Organization,
        ocr_evidence: Optional[OCREvidence] = None
    ) -> Tuple[int, List[str], str]:
        """
        Calculate overall anomaly score.
        Returns: (score 0-100, list of detected anomalies, status)
        """
        all_anomalies = []
        total_score = 0
        
        # Amount anomalies
        amount_anomalies, amount_score = cls.detect_amount_anomalies(extracted_data, organization)
        all_anomalies.extend(amount_anomalies)
        total_score += amount_score
        
        # Date anomalies
        date_anomalies, date_score = cls.detect_date_anomalies(extracted_data, organization)
        all_anomalies.extend(date_anomalies)
        total_score += date_score
        
        # Format anomalies
        format_anomalies, format_score = cls.detect_format_anomalies(extracted_data, ocr_evidence)
        all_anomalies.extend(format_anomalies)
        total_score += format_score
        
        # Determine status
        if total_score >= 70:
            status = 'critical_anomaly'
        elif total_score >= 50:
            status = 'high_anomaly'
        elif total_score >= 25:
            status = 'medium_anomaly'
        elif total_score > 0:
            status = 'low_anomaly'
        else:
            status = 'no_anomaly'
        
        return min(total_score, 100), all_anomalies, status


class RiskScoringService:
    """Calculates overall risk scores for invoices"""
    
    @staticmethod
    def calculate_risk_score(
        validation_results: Dict[str, Any],
        duplicate_score: int,
        anomaly_score: int,
        extracted_data: ExtractedData
    ) -> Tuple[int, str, List[str]]:
        """
        Calculate overall risk score combining all factors.
        Returns: (score 0-100, risk_level, risk_factors)
        """
        risk_factors = []
        total_score = 0
        
        # Validation failures (high impact)
        for check, result in validation_results.items():
            if result['status'] == 'fail':
                total_score += 25
                risk_factors.append(f"Failed {check} validation")
            elif result['status'] == 'warning':
                total_score += 10
                risk_factors.append(f"Warning in {check} validation")
        
        # Duplicate risk (high impact)
        total_score += duplicate_score // 2
        if duplicate_score > 50:
            risk_factors.append(f"Potential duplicate detected (score: {duplicate_score})")
        
        # Anomaly detection (medium impact)
        total_score += anomaly_score // 2
        if anomaly_score > 50:
            risk_factors.append(f"Anomalies detected (score: {anomaly_score})")
        
        # Missing critical fields
        if not extracted_data.invoice_number:
            total_score += 15
            risk_factors.append("Missing invoice number")
        if not extracted_data.vendor_name:
            total_score += 15
            risk_factors.append("Missing vendor information")
        if not extracted_data.total_amount:
            total_score += 20
            risk_factors.append("Missing total amount")
        
        # CAP score at 100
        risk_score = min(total_score, 100)
        
        # Determine risk level
        if risk_score >= 80:
            risk_level = 'critical'
        elif risk_score >= 60:
            risk_level = 'high'
        elif risk_score >= 30:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return risk_score, risk_level, risk_factors


class RecommendationService:
    """Generates approval recommendations"""
    
    @staticmethod
    def generate_recommendation(
        risk_score: int,
        risk_level: str,
        validation_results: Dict[str, Any],
        duplicate_score: int,
        extracted_data: ExtractedData
    ) -> Tuple[str, str]:
        """
        Generate approval recommendation.
        Returns: (recommendation, reason)
        """
        reason = []
        
        # High risk
        if risk_level == 'critical' or risk_score >= 80:
            reason.append(f"Critical risk detected ({risk_score}/100)")
            if duplicate_score >= 80:
                reason.append("Likely duplicate invoice")
            
            # Check specific validations
            for check, result in validation_results.items():
                if result['status'] == 'fail':
                    reason.append(f"{check} validation failed")
            
            return 'reject', '; '.join(reason)
        
        elif risk_level == 'high' or risk_score >= 60:
            reason.append(f"High risk level ({risk_score}/100)")
            return 'manual_review', '; '.join(reason)
        
        elif risk_level == 'medium' and risk_score >= 30:
            reason.append(f"Medium risk level ({risk_score}/100)")
            if duplicate_score >= 30:
                reason.append("Review for potential duplicates")
            return 'manual_review', '; '.join(reason)
        
        else:
            reason.append(f"Low risk detected ({risk_score}/100)")
            reason.append("All validations passed")
            return 'approve', '; '.join(reason)


class InvoiceAuditReportService:
    """Main service for comprehensive audit report generation"""
    
    def __init__(self, user: Optional[User] = None):
        self.user = user
        self.openai_service = OpenAIService()
    
    def generate_audit_trail(self, extracted_data: ExtractedData) -> Dict[str, Any]:
        """Generate audit trail from existing audit trail records"""
        trail = []
        
        try:
            audit_trails = AuditTrail.objects.filter(
                extracted_data=extracted_data
            ).order_by('event_time')
            
            for event in audit_trails:
                trail.append({
                    'timestamp': event.event_time.isoformat(),
                    'event': event.event_type,
                    'status': 'success' if event.success else 'failed',
                    'title': event.title,
                    'description': event.description,
                })
        except Exception as e:
            logger.error(f"Error generating audit trail: {e}")
        
        return trail
    
    def generate_comprehensive_report(
        self,
        extracted_data: ExtractedData,
        document: Document,
        organization: Organization,
        ocr_evidence: Optional[OCREvidence] = None
    ) -> InvoiceAuditReport:
        """
        Generate comprehensive audit report with all sections.
        
        Sections:
        1. Document Information
        2. Invoice Data Extraction  
        3. Line Items Details
        4. Financial Totals
        5. Validation Results
        6. Compliance Checks
        7. Duplicate Detection
        8. Anomaly Detection
        9. Risk Assessment
        10. AI Summary & Recommendations
        11. Audit Trail
        """
        
        try:
            # Run validations
            validation_results = DataValidationService.validate_all(extracted_data)
            
            # Duplicate detection
            duplicate_score, matched_docs, duplicate_status = DuplicateDetectionService.calculate_duplicate_score(
                extracted_data, organization
            )
            
            # Anomaly detection
            anomaly_score, anomalies, anomaly_status = AnomalyDetectionService.calculate_anomaly_score(
                extracted_data, organization, ocr_evidence
            )
            
            # Risk scoring
            risk_score, risk_level, risk_factors = RiskScoringService.calculate_risk_score(
                validation_results, duplicate_score, anomaly_score, extracted_data
            )
            
            # Generate recommendation
            recommendation, recommendation_reason = RecommendationService.generate_recommendation(
                risk_score, risk_level, validation_results, duplicate_score, extracted_data
            )
            
            # Generate AI summary if OpenAI is configured
            ai_summary = ""
            ai_summary_ar = ""
            ai_findings = ""
            ai_findings_ar = ""
            
            try:
                ai_summary = self.openai_service.generate_invoice_summary(
                    extracted_data, risk_level, anomalies
                )
                ai_findings = self.openai_service.generate_audit_findings(
                    extracted_data, validation_results, anomalies
                )
            except Exception as e:
                logger.warning(f"AI summary generation failed: {e}")
            
            # Prepare audit trail
            audit_trail = self.generate_audit_trail(extracted_data)
            
            # Create audit report record
            report_number = f"AR-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
            
            report_defaults = dict(
                document=document,
                organization=organization,
                ocr_evidence=ocr_evidence,
                report_number=report_number,
                status='generated',
                
                # Document Information
                upload_date=document.uploaded_at,
                ocr_engine=ocr_evidence.ocr_engine if ocr_evidence else 'unknown',
                ocr_confidence_score=ocr_evidence.confidence_score if ocr_evidence else 0,
                processing_status=document.status,
                
                # Invoice Data
                extracted_invoice_number=extracted_data.invoice_number,
                extracted_issue_date=extracted_data.invoice_date,
                extracted_due_date=extracted_data.due_date,
                extracted_vendor_name=extracted_data.vendor_name,
                extracted_vendor_address=ocr_evidence.extracted_vendor_address if ocr_evidence else "",
                extracted_customer_name=extracted_data.customer_name,
                extracted_customer_address=ocr_evidence.extracted_customer_address if ocr_evidence else "",
                
                # Line Items
                line_items_json=extracted_data.items_json or [],
                
                # Financial Totals
                subtotal_amount=extracted_data.total_amount - (extracted_data.tax_amount or 0) if extracted_data.total_amount else None,
                vat_amount=extracted_data.tax_amount,
                total_amount=extracted_data.total_amount,
                currency=extracted_data.currency or 'SAR',
                
                # Validation Results
                validation_results_json=validation_results,
                
                # Duplicate Detection
                duplicate_score=duplicate_score,
                duplicate_matched_documents_json=[{'id': doc_id} for doc_id in matched_docs],
                duplicate_status=duplicate_status,
                
                # Anomaly Detection
                anomaly_score=anomaly_score,
                anomaly_status=anomaly_status,
                anomaly_explanation='\n'.join(anomalies) if anomalies else 'No anomalies detected',
                anomaly_reasons_json=[{'reason': a, 'type': 'detected'} for a in anomalies],
                
                # Risk Assessment
                risk_score=risk_score,
                risk_level=risk_level,
                risk_factors_json=risk_factors,
                
                # AI Summary
                ai_summary=ai_summary,
                ai_summary_ar=ai_summary_ar,
                ai_findings=ai_findings,
                ai_findings_ar=ai_findings_ar,
                ai_review_required=risk_level in ['high', 'critical'],
                
                # Recommendations
                recommendation=recommendation,
                recommendation_reason=recommendation_reason,
                
                # Audit Trail
                audit_trail_json=audit_trail,
                
                # Generated by
                generated_by=self.user,
            )

            report, created = InvoiceAuditReport.objects.update_or_create(
                extracted_data=extracted_data,
                defaults=report_defaults,
            )

            arabic_presentation = build_report_presentation(report, lang='ar')
            report.ai_summary_ar = arabic_presentation['ai_summary_display']
            report.ai_findings_ar = arabic_presentation['ai_findings_display']
            report.recommendation_reason_ar = arabic_presentation['recommendation_reason_display']

            # Create full report JSON
            report.full_report_json = self._create_full_report_json(report)
            report.save(update_fields=['ai_summary_ar', 'ai_findings_ar', 'recommendation_reason_ar', 'full_report_json'])
            
            logger.info(f"Audit report generated: {report_number} for document {document.id}")
            
            # Log the generation in audit trail
            AuditTrail.objects.create(
                extracted_data=extracted_data,
                organization=organization,
                event_type='audit_summary',
                severity='info',
                title='Audit Report Generated',
                description=f'Comprehensive audit report generated: {report_number}',
                performed_by=self.user,
                success=True,
                result_summary=f'Risk Level: {risk_level}, Recommendation: {recommendation}'
            )
            
            return report
        
        except Exception as e:
            logger.error(f"Error generating audit report: {e}", exc_info=True)
            raise
    
    def _create_full_report_json(self, report: InvoiceAuditReport) -> Dict[str, Any]:
        """Create a complete JSON representation of the audit report"""
        return {
            'report_number': report.report_number,
            'generated_at': report.generated_at.isoformat() if report.generated_at else None,
            'status': report.status,
            
            # Document Information
            'document': {
                'id': str(report.document.id),
                'file_name': report.document.file_name,
                'upload_date': report.upload_date.isoformat() if report.upload_date else None,
                'ocr_engine': report.ocr_engine,
                'ocr_confidence': report.ocr_confidence_score,
                'processing_status': report.processing_status,
            },
            
            # Invoice Data
            'invoice_data': {
                'invoice_number': report.extracted_invoice_number,
                'issue_date': report.extracted_issue_date.isoformat() if report.extracted_issue_date else None,
                'due_date': report.extracted_due_date.isoformat() if report.extracted_due_date else None,
                'vendor': report.extracted_vendor_name,
                'vendor_address': report.extracted_vendor_address,
                'customer': report.extracted_customer_name,
                'customer_address': report.extracted_customer_address,
            },
            
            # Line Items
            'line_items': report.line_items_json or [],
            
            # Financial Totals
            'financial_totals': {
                'subtotal': str(report.subtotal_amount) if report.subtotal_amount else None,
                'vat': str(report.vat_amount) if report.vat_amount else None,
                'total': str(report.total_amount) if report.total_amount else None,
                'currency': report.currency,
            },
            
            # Validation Results
            'validation_results': report.validation_results_json,
            
            # Duplicate Detection
            'duplicate_detection': {
                'score': report.duplicate_score,
                'status': report.duplicate_status,
                'matched_documents': report.duplicate_matched_documents_json or [],
            },
            
            # Anomaly Detection
            'anomaly_detection': {
                'score': report.anomaly_score,
                'status': report.anomaly_status,
                'explanation': report.anomaly_explanation,
                'reasons': report.anomaly_reasons_json or [],
            },
            
            # Risk Assessment
            'risk_assessment': {
                'score': report.risk_score,
                'level': report.risk_level,
                'factors': report.risk_factors_json or [],
            },
            
            # AI Analysis
            'ai_analysis': {
                'summary': report.ai_summary,
                'summary_ar': report.ai_summary_ar,
                'findings': report.ai_findings,
                'findings_ar': report.ai_findings_ar,
                'review_required': report.ai_review_required,
            },
            
            # Recommendation
            'recommendation': {
                'action': report.recommendation,
                'reason': report.recommendation_reason,
                'reason_ar': report.recommendation_reason_ar,
            },
            
            # Audit Trail
            'audit_trail': report.audit_trail_json or [],
        }
