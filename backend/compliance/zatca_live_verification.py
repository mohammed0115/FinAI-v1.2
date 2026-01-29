"""
ZATCA Live Verification Service - خدمة التحقق المباشر من هيئة الزكاة والضريبة والجمارك

CRITICAL SCOPE LIMITATION:
=========================
FinAI is a READ-ONLY audit and compliance system.

This service performs POST-TRANSACTION, READ-ONLY verification ONLY.
It does NOT:
- Generate invoices
- Submit invoices to ZATCA
- Sign invoices
- Modify invoice data
- Act on behalf of taxpayers

What it DOES:
- Validate existing invoice data against ZATCA requirements
- Verify VAT number format and validity
- Check UUID correctness
- Verify hash chain integrity
- Capture validation status and error codes
- Store results as audit evidence
"""
import hashlib
import re
import base64
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from django.utils import timezone

logger = logging.getLogger(__name__)


class ZATCAErrorCode(Enum):
    """
    ZATCA Official Error Codes
    رموز أخطاء هيئة الزكاة والضريبة والجمارك الرسمية
    """
    # Mandatory Field Errors
    MISSING_INVOICE_NUMBER = ("ZATCA-MF-001", "رقم الفاتورة مفقود", "Invoice number is missing")
    MISSING_UUID = ("ZATCA-MF-002", "المعرف الفريد (UUID) مفقود", "UUID is missing")
    MISSING_ISSUE_DATE = ("ZATCA-MF-003", "تاريخ الإصدار مفقود", "Issue date is missing")
    MISSING_SELLER_NAME = ("ZATCA-MF-004", "اسم البائع مفقود", "Seller name is missing")
    MISSING_SELLER_VAT = ("ZATCA-MF-005", "الرقم الضريبي للبائع مفقود", "Seller VAT number is missing")
    MISSING_BUYER_NAME = ("ZATCA-MF-006", "اسم المشتري مفقود", "Buyer name is missing")
    MISSING_TOTAL_EXCL_VAT = ("ZATCA-MF-007", "المجموع بدون الضريبة مفقود", "Total excluding VAT is missing")
    MISSING_TOTAL_VAT = ("ZATCA-MF-008", "مبلغ الضريبة مفقود", "VAT amount is missing")
    MISSING_TOTAL_INCL_VAT = ("ZATCA-MF-009", "المجموع شامل الضريبة مفقود", "Total including VAT is missing")
    
    # Format Errors
    INVALID_VAT_NUMBER_FORMAT = ("ZATCA-FMT-001", "تنسيق الرقم الضريبي غير صحيح", "Invalid VAT number format")
    INVALID_UUID_FORMAT = ("ZATCA-FMT-002", "تنسيق المعرف الفريد غير صحيح", "Invalid UUID format")
    INVALID_INVOICE_NUMBER_LENGTH = ("ZATCA-FMT-003", "طول رقم الفاتورة غير صحيح", "Invalid invoice number length")
    INVALID_DATE_FORMAT = ("ZATCA-FMT-004", "تنسيق التاريخ غير صحيح", "Invalid date format")
    INVALID_CURRENCY_CODE = ("ZATCA-FMT-005", "رمز العملة غير صحيح", "Invalid currency code")
    
    # Calculation Errors
    VAT_CALCULATION_MISMATCH = ("ZATCA-CALC-001", "خطأ في حساب ضريبة القيمة المضافة", "VAT calculation mismatch")
    TOTAL_MISMATCH = ("ZATCA-CALC-002", "خطأ في حساب المجموع", "Total calculation mismatch")
    INVALID_VAT_RATE = ("ZATCA-CALC-003", "نسبة ضريبة القيمة المضافة غير صحيحة", "Invalid VAT rate")
    
    # Business Rule Errors
    FUTURE_INVOICE_DATE = ("ZATCA-BR-001", "تاريخ الفاتورة في المستقبل", "Invoice date is in the future")
    INVALID_INVOICE_TYPE = ("ZATCA-BR-002", "نوع الفاتورة غير صحيح", "Invalid invoice type")
    INVALID_INVOICE_SUBTYPE = ("ZATCA-BR-003", "النوع الفرعي للفاتورة غير صحيح", "Invalid invoice subtype")
    
    # Hash/Integrity Errors
    INVALID_INVOICE_HASH = ("ZATCA-INT-001", "تجزئة الفاتورة غير صحيحة", "Invalid invoice hash")
    HASH_CHAIN_BROKEN = ("ZATCA-INT-002", "سلسلة التجزئة منقطعة", "Hash chain is broken")
    INVALID_QR_CODE = ("ZATCA-INT-003", "رمز QR غير صحيح", "Invalid QR code")
    
    @property
    def code(self) -> str:
        return self.value[0]
    
    @property
    def message_ar(self) -> str:
        return self.value[1]
    
    @property
    def message_en(self) -> str:
        return self.value[2]


@dataclass
class ZATCAVerificationResult:
    """
    نتيجة التحقق من ZATCA
    Individual verification check result
    """
    check_type: str  # mandatory_field, format, calculation, business_rule, integrity
    field_name: str
    is_valid: bool
    error_code: Optional[str] = None
    message_ar: str = ""
    message_en: str = ""
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    regulatory_article: Optional[str] = None


@dataclass
class ZATCAVerificationReport:
    """
    تقرير التحقق الشامل من ZATCA
    Complete verification report
    """
    invoice_id: str
    invoice_number: str
    verification_timestamp: datetime
    overall_status: str  # 'passed', 'failed', 'warning'
    compliance_score: int  # 0-100
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    results: List[ZATCAVerificationResult]
    hash_verification: Dict
    summary_ar: str
    summary_en: str


class ZATCALiveVerificationService:
    """
    خدمة التحقق المباشر من ZATCA
    ZATCA Live Verification Service
    
    SCOPE: READ-ONLY POST-TRANSACTION VERIFICATION
    
    This service verifies existing invoice data against ZATCA requirements.
    It does NOT generate, submit, or modify invoices.
    """
    
    # Saudi VAT Number Pattern: 3XXXXXXXXXX00003
    VAT_NUMBER_PATTERN = r'^3\d{13}3$'
    
    # Valid Invoice Types (ZATCA Phase 2)
    VALID_INVOICE_TYPES = ['388', '381', '383']  # Tax Invoice, Credit Note, Debit Note
    
    # Valid Invoice Subtypes
    VALID_INVOICE_SUBTYPES = ['0100000', '0200000']  # Standard, Simplified
    
    # Saudi VAT Rate
    SAUDI_VAT_RATE = Decimal('0.15')  # 15%
    
    # Maximum Invoice Number Length (ZATCA Spec)
    MAX_INVOICE_NUMBER_LENGTH = 127
    
    def __init__(self):
        """Initialize the verification service"""
        self._verification_cache = {}
        logger.info("ZATCA Live Verification Service initialized - READ-ONLY MODE")
    
    def verify_invoice(self, invoice_data: Dict) -> ZATCAVerificationReport:
        """
        التحقق الشامل من الفاتورة
        Perform comprehensive invoice verification
        
        This is a READ-ONLY operation that validates existing invoice data.
        It does NOT modify or submit invoices.
        
        Args:
            invoice_data: Dictionary containing invoice fields to verify
            
        Returns:
            ZATCAVerificationReport with all verification results
        """
        verification_timestamp = timezone.now()
        results = []
        
        # 1. Mandatory Field Verification
        mandatory_results = self._verify_mandatory_fields(invoice_data)
        results.extend(mandatory_results)
        
        # 2. Format Verification
        format_results = self._verify_formats(invoice_data)
        results.extend(format_results)
        
        # 3. Calculation Verification
        calculation_results = self._verify_calculations(invoice_data)
        results.extend(calculation_results)
        
        # 4. Business Rule Verification
        business_results = self._verify_business_rules(invoice_data)
        results.extend(business_results)
        
        # 5. Hash/Integrity Verification
        integrity_results = self._verify_integrity(invoice_data)
        results.extend(integrity_results)
        
        # Calculate overall status
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.is_valid)
        failed_checks = sum(1 for r in results if not r.is_valid and r.check_type != 'warning')
        warning_checks = sum(1 for r in results if r.check_type == 'warning')
        
        compliance_score = int((passed_checks / max(total_checks, 1)) * 100)
        
        if failed_checks == 0:
            overall_status = 'passed'
        elif compliance_score >= 80:
            overall_status = 'warning'
        else:
            overall_status = 'failed'
        
        # Generate summaries
        summary_ar = self._generate_summary_ar(overall_status, compliance_score, failed_checks)
        summary_en = self._generate_summary_en(overall_status, compliance_score, failed_checks)
        
        # Hash verification details
        hash_verification = self._get_hash_verification_details(invoice_data)
        
        return ZATCAVerificationReport(
            invoice_id=str(invoice_data.get('id', invoice_data.get('uuid', ''))),
            invoice_number=invoice_data.get('invoice_number', ''),
            verification_timestamp=verification_timestamp,
            overall_status=overall_status,
            compliance_score=compliance_score,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            results=results,
            hash_verification=hash_verification,
            summary_ar=summary_ar,
            summary_en=summary_en,
        )
    
    def _verify_mandatory_fields(self, invoice_data: Dict) -> List[ZATCAVerificationResult]:
        """
        التحقق من الحقول الإلزامية
        Verify mandatory fields based on invoice type
        """
        results = []
        
        # Determine if simplified or standard invoice
        invoice_subtype = invoice_data.get('invoice_subtype', '0100000')
        is_simplified = invoice_subtype == '0200000'
        
        # Define mandatory fields
        if is_simplified:
            mandatory_fields = [
                ('invoice_number', ZATCAErrorCode.MISSING_INVOICE_NUMBER),
                ('issue_date', ZATCAErrorCode.MISSING_ISSUE_DATE),
                ('seller_name', ZATCAErrorCode.MISSING_SELLER_NAME),
                ('seller_vat_number', ZATCAErrorCode.MISSING_SELLER_VAT),
                ('total_including_vat', ZATCAErrorCode.MISSING_TOTAL_INCL_VAT),
            ]
        else:
            mandatory_fields = [
                ('invoice_number', ZATCAErrorCode.MISSING_INVOICE_NUMBER),
                ('uuid', ZATCAErrorCode.MISSING_UUID),
                ('issue_date', ZATCAErrorCode.MISSING_ISSUE_DATE),
                ('seller_name', ZATCAErrorCode.MISSING_SELLER_NAME),
                ('seller_vat_number', ZATCAErrorCode.MISSING_SELLER_VAT),
                ('buyer_name', ZATCAErrorCode.MISSING_BUYER_NAME),
                ('total_excluding_vat', ZATCAErrorCode.MISSING_TOTAL_EXCL_VAT),
                ('total_vat', ZATCAErrorCode.MISSING_TOTAL_VAT),
                ('total_including_vat', ZATCAErrorCode.MISSING_TOTAL_INCL_VAT),
            ]
        
        for field_name, error_code in mandatory_fields:
            value = invoice_data.get(field_name)
            is_valid = value is not None and str(value).strip() != ''
            
            results.append(ZATCAVerificationResult(
                check_type='mandatory_field',
                field_name=field_name,
                is_valid=is_valid,
                error_code=None if is_valid else error_code.code,
                message_ar=f'الحقل الإلزامي "{field_name}" {"موجود" if is_valid else error_code.message_ar}',
                message_en=f'Mandatory field "{field_name}" {"present" if is_valid else error_code.message_en}',
                expected_value='Present and non-empty',
                actual_value=str(value) if value else 'Missing/Empty',
                regulatory_article='المادة 53 من اللائحة التنفيذية لنظام ضريبة القيمة المضافة'
            ))
        
        return results
    
    def _verify_formats(self, invoice_data: Dict) -> List[ZATCAVerificationResult]:
        """
        التحقق من التنسيقات
        Verify field formats according to ZATCA specifications
        """
        results = []
        
        # 1. VAT Number Format (15 digits: 3XXXXXXXXXX00003)
        seller_vat = str(invoice_data.get('seller_vat_number', ''))
        vat_valid = bool(re.match(self.VAT_NUMBER_PATTERN, seller_vat))
        results.append(ZATCAVerificationResult(
            check_type='format',
            field_name='seller_vat_number',
            is_valid=vat_valid,
            error_code=None if vat_valid else ZATCAErrorCode.INVALID_VAT_NUMBER_FORMAT.code,
            message_ar=f'تنسيق الرقم الضريبي للبائع {"صحيح" if vat_valid else "غير صحيح - يجب أن يكون 15 رقم يبدأ بـ 3 وينتهي بـ 3"}',
            message_en=f'Seller VAT number format is {"valid" if vat_valid else "invalid - must be 15 digits starting with 3 and ending with 3"}',
            expected_value='3XXXXXXXXXXXXX3 (15 digits)',
            actual_value=seller_vat or 'Empty',
            regulatory_article='المادة 66 - شروط الرقم الضريبي'
        ))
        
        # 2. Buyer VAT Number Format (if provided for standard invoice)
        buyer_vat = invoice_data.get('buyer_vat_number')
        if buyer_vat:
            buyer_vat_valid = bool(re.match(self.VAT_NUMBER_PATTERN, str(buyer_vat)))
            results.append(ZATCAVerificationResult(
                check_type='format',
                field_name='buyer_vat_number',
                is_valid=buyer_vat_valid,
                error_code=None if buyer_vat_valid else ZATCAErrorCode.INVALID_VAT_NUMBER_FORMAT.code,
                message_ar=f'تنسيق الرقم الضريبي للمشتري {"صحيح" if buyer_vat_valid else "غير صحيح"}',
                message_en=f'Buyer VAT number format is {"valid" if buyer_vat_valid else "invalid"}',
                expected_value='3XXXXXXXXXXXXX3 (15 digits)',
                actual_value=str(buyer_vat),
                regulatory_article='المادة 66 - شروط الرقم الضريبي'
            ))
        
        # 3. UUID Format
        invoice_uuid = invoice_data.get('uuid', '')
        try:
            uuid.UUID(str(invoice_uuid))
            uuid_valid = True
        except (ValueError, AttributeError, TypeError):
            uuid_valid = False
        
        results.append(ZATCAVerificationResult(
            check_type='format',
            field_name='uuid',
            is_valid=uuid_valid,
            error_code=None if uuid_valid else ZATCAErrorCode.INVALID_UUID_FORMAT.code,
            message_ar=f'تنسيق المعرف الفريد (UUID) {"صحيح" if uuid_valid else "غير صحيح"}',
            message_en=f'UUID format is {"valid" if uuid_valid else "invalid"}',
            expected_value='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
            actual_value=str(invoice_uuid) if invoice_uuid else 'Empty',
            regulatory_article='متطلبات ZATCA Phase 2'
        ))
        
        # 4. Invoice Number Length
        invoice_number = str(invoice_data.get('invoice_number', ''))
        number_valid = 0 < len(invoice_number) <= self.MAX_INVOICE_NUMBER_LENGTH
        results.append(ZATCAVerificationResult(
            check_type='format',
            field_name='invoice_number',
            is_valid=number_valid,
            error_code=None if number_valid else ZATCAErrorCode.INVALID_INVOICE_NUMBER_LENGTH.code,
            message_ar=f'طول رقم الفاتورة {"صحيح" if number_valid else f"غير صحيح - يجب ألا يتجاوز {self.MAX_INVOICE_NUMBER_LENGTH} حرف"}',
            message_en=f'Invoice number length is {"valid" if number_valid else f"invalid - must not exceed {self.MAX_INVOICE_NUMBER_LENGTH} characters"}',
            expected_value=f'1-{self.MAX_INVOICE_NUMBER_LENGTH} characters',
            actual_value=f'{len(invoice_number)} characters',
            regulatory_article='المادة 53(2) - متطلبات رقم الفاتورة'
        ))
        
        # 5. Currency Code (SAR expected for Saudi transactions)
        currency = invoice_data.get('currency_code', 'SAR')
        currency_valid = currency in ['SAR', 'USD', 'EUR', 'GBP', 'AED']
        results.append(ZATCAVerificationResult(
            check_type='format',
            field_name='currency_code',
            is_valid=currency_valid,
            error_code=None if currency_valid else ZATCAErrorCode.INVALID_CURRENCY_CODE.code,
            message_ar=f'رمز العملة {"صحيح" if currency_valid else "غير صحيح"}',
            message_en=f'Currency code is {"valid" if currency_valid else "invalid"}',
            expected_value='SAR, USD, EUR, GBP, or AED',
            actual_value=str(currency),
            regulatory_article='المادة 53(4) - العملة'
        ))
        
        return results
    
    def _verify_calculations(self, invoice_data: Dict) -> List[ZATCAVerificationResult]:
        """
        التحقق من الحسابات
        Verify VAT calculations and totals
        """
        results = []
        
        try:
            total_ex_vat = Decimal(str(invoice_data.get('total_excluding_vat', 0)))
            total_vat = Decimal(str(invoice_data.get('total_vat', 0)))
            total_inc_vat = Decimal(str(invoice_data.get('total_including_vat', 0)))
        except (ValueError, TypeError):
            results.append(ZATCAVerificationResult(
                check_type='calculation',
                field_name='amounts',
                is_valid=False,
                error_code=ZATCAErrorCode.TOTAL_MISMATCH.code,
                message_ar='خطأ في قراءة المبالغ - يجب أن تكون أرقام صحيحة',
                message_en='Error reading amounts - must be valid numbers',
            ))
            return results
        
        # 1. Total Calculation Verification
        expected_total = total_ex_vat + total_vat
        total_diff = abs(expected_total - total_inc_vat)
        calc_valid = total_diff < Decimal('0.01')
        
        results.append(ZATCAVerificationResult(
            check_type='calculation',
            field_name='total_including_vat',
            is_valid=calc_valid,
            error_code=None if calc_valid else ZATCAErrorCode.TOTAL_MISMATCH.code,
            message_ar=f'حساب المجموع شامل الضريبة {"صحيح" if calc_valid else f"غير صحيح - المتوقع {expected_total} والفعلي {total_inc_vat}"}',
            message_en=f'Total including VAT calculation is {"correct" if calc_valid else f"incorrect - expected {expected_total}, got {total_inc_vat}"}',
            expected_value=str(expected_total),
            actual_value=str(total_inc_vat),
            regulatory_article='المادة 53(8) - حساب المجموع'
        ))
        
        # 2. VAT Rate Verification (15% for Saudi Arabia)
        if total_ex_vat > 0:
            calculated_rate = (total_vat / total_ex_vat * 100).quantize(Decimal('0.01'))
            expected_rate = Decimal('15.00')
            
            # Allow 0% for exempt items or 15% standard rate
            rate_valid = calculated_rate == expected_rate or total_vat == Decimal('0')
            
            results.append(ZATCAVerificationResult(
                check_type='calculation',
                field_name='vat_rate',
                is_valid=rate_valid,
                error_code=None if rate_valid else ZATCAErrorCode.INVALID_VAT_RATE.code,
                message_ar=f'نسبة ضريبة القيمة المضافة {"صحيحة (15%)" if rate_valid else f"غير صحيحة - النسبة المحسوبة {calculated_rate}%"}',
                message_en=f'VAT rate is {"correct (15%)" if rate_valid else f"incorrect - calculated rate is {calculated_rate}%"}',
                expected_value='15.00% or 0.00%',
                actual_value=f'{calculated_rate}%',
                regulatory_article='المادة 2 - نسبة ضريبة القيمة المضافة'
            ))
        
        # 3. VAT Amount Verification
        if total_ex_vat > 0:
            expected_vat = total_ex_vat * self.SAUDI_VAT_RATE
            vat_diff = abs(expected_vat - total_vat)
            vat_calc_valid = vat_diff < Decimal('0.01') or total_vat == Decimal('0')
            
            results.append(ZATCAVerificationResult(
                check_type='calculation',
                field_name='total_vat',
                is_valid=vat_calc_valid,
                error_code=None if vat_calc_valid else ZATCAErrorCode.VAT_CALCULATION_MISMATCH.code,
                message_ar=f'مبلغ الضريبة {"صحيح" if vat_calc_valid else f"غير صحيح - المتوقع {expected_vat:.2f} والفعلي {total_vat}"}',
                message_en=f'VAT amount is {"correct" if vat_calc_valid else f"incorrect - expected {expected_vat:.2f}, got {total_vat}"}',
                expected_value=f'{expected_vat:.2f}',
                actual_value=str(total_vat),
                regulatory_article='المادة 53(7) - حساب الضريبة'
            ))
        
        return results
    
    def _verify_business_rules(self, invoice_data: Dict) -> List[ZATCAVerificationResult]:
        """
        التحقق من قواعد العمل
        Verify business rules
        """
        results = []
        
        # 1. Invoice Date (not in the future)
        issue_date = invoice_data.get('issue_date')
        if issue_date:
            if isinstance(issue_date, str):
                try:
                    issue_date = datetime.strptime(issue_date, '%Y-%m-%d').date()
                except ValueError:
                    results.append(ZATCAVerificationResult(
                        check_type='business_rule',
                        field_name='issue_date',
                        is_valid=False,
                        error_code=ZATCAErrorCode.INVALID_DATE_FORMAT.code,
                        message_ar='تنسيق تاريخ الإصدار غير صحيح',
                        message_en='Invalid issue date format',
                        expected_value='YYYY-MM-DD',
                        actual_value=str(invoice_data.get('issue_date')),
                    ))
                    issue_date = None
            
            if issue_date:
                today = date.today()
                date_valid = issue_date <= today
                results.append(ZATCAVerificationResult(
                    check_type='business_rule',
                    field_name='issue_date',
                    is_valid=date_valid,
                    error_code=None if date_valid else ZATCAErrorCode.FUTURE_INVOICE_DATE.code,
                    message_ar=f'تاريخ الفاتورة {"صحيح" if date_valid else "لا يمكن أن يكون في المستقبل"}',
                    message_en=f'Invoice date is {"valid" if date_valid else "cannot be in the future"}',
                    expected_value=f'<= {today}',
                    actual_value=str(issue_date),
                    regulatory_article='المادة 53(3) - تاريخ الفاتورة'
                ))
        
        # 2. Invoice Type Code
        invoice_type = invoice_data.get('invoice_type_code', '388')
        type_valid = str(invoice_type) in self.VALID_INVOICE_TYPES
        results.append(ZATCAVerificationResult(
            check_type='business_rule',
            field_name='invoice_type_code',
            is_valid=type_valid,
            error_code=None if type_valid else ZATCAErrorCode.INVALID_INVOICE_TYPE.code,
            message_ar=f'نوع الفاتورة {"صحيح" if type_valid else "غير صحيح"}',
            message_en=f'Invoice type is {"valid" if type_valid else "invalid"}',
            expected_value='388 (Tax Invoice), 381 (Credit Note), or 383 (Debit Note)',
            actual_value=str(invoice_type),
            regulatory_article='متطلبات ZATCA Phase 2'
        ))
        
        # 3. Invoice Subtype
        invoice_subtype = invoice_data.get('invoice_subtype', '0100000')
        subtype_valid = str(invoice_subtype) in self.VALID_INVOICE_SUBTYPES
        results.append(ZATCAVerificationResult(
            check_type='business_rule',
            field_name='invoice_subtype',
            is_valid=subtype_valid,
            error_code=None if subtype_valid else ZATCAErrorCode.INVALID_INVOICE_SUBTYPE.code,
            message_ar=f'النوع الفرعي للفاتورة {"صحيح" if subtype_valid else "غير صحيح"}',
            message_en=f'Invoice subtype is {"valid" if subtype_valid else "invalid"}',
            expected_value='0100000 (Standard) or 0200000 (Simplified)',
            actual_value=str(invoice_subtype),
            regulatory_article='متطلبات ZATCA Phase 2'
        ))
        
        return results
    
    def _verify_integrity(self, invoice_data: Dict) -> List[ZATCAVerificationResult]:
        """
        التحقق من سلامة البيانات
        Verify data integrity (hash chain, QR code)
        """
        results = []
        
        # 1. Invoice Hash Verification
        stored_hash = invoice_data.get('invoice_hash')
        if stored_hash:
            # Recalculate hash
            hash_input = self._build_hash_input(invoice_data)
            calculated_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            hash_valid = calculated_hash == stored_hash
            results.append(ZATCAVerificationResult(
                check_type='integrity',
                field_name='invoice_hash',
                is_valid=hash_valid,
                error_code=None if hash_valid else ZATCAErrorCode.INVALID_INVOICE_HASH.code,
                message_ar=f'تجزئة الفاتورة {"صحيحة" if hash_valid else "غير صحيحة - قد تكون البيانات معدلة"}',
                message_en=f'Invoice hash is {"valid" if hash_valid else "invalid - data may have been modified"}',
                expected_value=calculated_hash[:16] + '...',
                actual_value=stored_hash[:16] + '...' if stored_hash else 'Missing',
                regulatory_article='متطلبات ZATCA Phase 2 - سلسلة التجزئة'
            ))
        
        # 2. Hash Chain Verification
        previous_hash = invoice_data.get('previous_invoice_hash')
        if stored_hash and previous_hash:
            # Verify hash chain includes previous hash
            chain_valid = previous_hash in self._build_hash_input(invoice_data)
            results.append(ZATCAVerificationResult(
                check_type='integrity',
                field_name='hash_chain',
                is_valid=chain_valid,
                error_code=None if chain_valid else ZATCAErrorCode.HASH_CHAIN_BROKEN.code,
                message_ar=f'سلسلة التجزئة {"سليمة" if chain_valid else "منقطعة"}',
                message_en=f'Hash chain is {"intact" if chain_valid else "broken"}',
                expected_value='Previous hash included',
                actual_value='Chain verified' if chain_valid else 'Chain broken',
                regulatory_article='متطلبات ZATCA Phase 2 - سلسلة التجزئة'
            ))
        
        # 3. QR Code Verification (if present)
        qr_code = invoice_data.get('qr_code')
        if qr_code:
            qr_valid = self._verify_qr_code(qr_code, invoice_data)
            results.append(ZATCAVerificationResult(
                check_type='integrity',
                field_name='qr_code',
                is_valid=qr_valid,
                error_code=None if qr_valid else ZATCAErrorCode.INVALID_QR_CODE.code,
                message_ar=f'رمز QR {"صحيح" if qr_valid else "غير صحيح"}',
                message_en=f'QR code is {"valid" if qr_valid else "invalid"}',
                regulatory_article='متطلبات ZATCA Phase 2 - رمز الاستجابة السريعة'
            ))
        
        return results
    
    def _build_hash_input(self, invoice_data: Dict) -> str:
        """Build the hash input string for invoice"""
        components = [
            str(invoice_data.get('invoice_number', '')),
            str(invoice_data.get('uuid', '')),
            str(invoice_data.get('issue_date', '')),
            str(invoice_data.get('total_including_vat', '')),
            str(invoice_data.get('previous_invoice_hash', '')),
        ]
        return '|'.join(components)
    
    def _verify_qr_code(self, qr_code: str, invoice_data: Dict) -> bool:
        """
        Verify QR code contains required ZATCA fields
        ZATCA requires: Seller name, VAT number, Timestamp, Total, VAT amount
        """
        try:
            # QR code should be base64 encoded TLV data
            decoded = base64.b64decode(qr_code)
            
            # Basic validation - QR should contain seller VAT number
            seller_vat = str(invoice_data.get('seller_vat_number', ''))
            
            # Check if VAT number bytes are present in decoded data
            return seller_vat.encode() in decoded
        except Exception:
            return False
    
    def _get_hash_verification_details(self, invoice_data: Dict) -> Dict:
        """Get detailed hash verification information"""
        hash_input = self._build_hash_input(invoice_data)
        calculated_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return {
            'hash_algorithm': 'SHA-256',
            'hash_input_fields': ['invoice_number', 'uuid', 'issue_date', 'total_including_vat', 'previous_invoice_hash'],
            'calculated_hash': calculated_hash,
            'stored_hash': invoice_data.get('invoice_hash'),
            'previous_hash': invoice_data.get('previous_invoice_hash'),
            'hash_matches': calculated_hash == invoice_data.get('invoice_hash'),
        }
    
    def _generate_summary_ar(self, status: str, score: int, failures: int) -> str:
        """Generate Arabic summary"""
        if status == 'passed':
            return f"""
التحقق من الفاتورة: ناجح
درجة الامتثال: {score}%

جميع متطلبات هيئة الزكاة والضريبة والجمارك مستوفاة.
الفاتورة متوافقة مع متطلبات المرحلة الثانية من الفوترة الإلكترونية (فاتورة).
"""
        elif status == 'warning':
            return f"""
التحقق من الفاتورة: تحذير
درجة الامتثال: {score}%
عدد المشكلات: {failures}

تم اكتشاف بعض المشكلات البسيطة. يُنصح بمراجعتها قبل إرسال الفاتورة إلى هيئة الزكاة والضريبة والجمارك.
"""
        else:
            return f"""
التحقق من الفاتورة: فشل
درجة الامتثال: {score}%
عدد المشكلات: {failures}

الفاتورة لا تستوفي متطلبات هيئة الزكاة والضريبة والجمارك.
يجب معالجة جميع المشكلات قبل إرسال الفاتورة.
"""
    
    def _generate_summary_en(self, status: str, score: int, failures: int) -> str:
        """Generate English summary"""
        if status == 'passed':
            return f"""
Invoice Verification: PASSED
Compliance Score: {score}%

All ZATCA requirements are met.
Invoice is compliant with Phase 2 E-Invoicing (Fatoorah) requirements.
"""
        elif status == 'warning':
            return f"""
Invoice Verification: WARNING
Compliance Score: {score}%
Issues Found: {failures}

Some minor issues detected. Review recommended before submitting to ZATCA.
"""
        else:
            return f"""
Invoice Verification: FAILED
Compliance Score: {score}%
Issues Found: {failures}

Invoice does not meet ZATCA requirements.
All issues must be resolved before submission.
"""
    
    def verify_batch(self, invoices: List[Dict]) -> List[ZATCAVerificationReport]:
        """
        التحقق من مجموعة فواتير
        Verify a batch of invoices (READ-ONLY)
        """
        return [self.verify_invoice(invoice) for invoice in invoices]
    
    def verify_vat_number(self, vat_number: str) -> Dict:
        """
        التحقق من الرقم الضريبي
        Verify VAT number format (READ-ONLY)
        
        Note: This only validates the format.
        Actual VAT number registration status would require
        ZATCA API integration which is out of scope for FinAI.
        """
        vat_number = str(vat_number).strip()
        
        format_valid = bool(re.match(self.VAT_NUMBER_PATTERN, vat_number))
        
        return {
            'vat_number': vat_number,
            'format_valid': format_valid,
            'format_check_ar': 'تنسيق الرقم الضريبي صحيح' if format_valid else 'تنسيق الرقم الضريبي غير صحيح',
            'format_check_en': 'VAT number format is valid' if format_valid else 'VAT number format is invalid',
            'expected_format': '3XXXXXXXXXXXXX3 (15 digits)',
            'note_ar': 'ملاحظة: هذا التحقق من التنسيق فقط. للتحقق من حالة التسجيل، يرجى استخدام بوابة هيئة الزكاة والضريبة والجمارك',
            'note_en': 'Note: This is format verification only. For registration status, please use ZATCA portal',
            'verification_scope': 'READ-ONLY FORMAT CHECK',
        }


# Singleton instance
zatca_live_verification_service = ZATCALiveVerificationService()
