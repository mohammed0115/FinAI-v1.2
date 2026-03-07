"""
Hard Rules Validators - مصادقات القواعد الصارمة

Individual validator classes for each category of hard rules.
All validators are DETERMINISTIC - no AI, no inference, no probabilistic logic.
"""
import re
import hashlib
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import uuid as uuid_module
import logging

logger = logging.getLogger(__name__)


class RuleStatus(Enum):
    """Rule evaluation status"""
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    WARNING = "WARNING"


@dataclass
class RuleResult:
    """Result of a single rule evaluation"""
    rule_id: str
    rule_name: str
    rule_name_ar: str
    category: str
    status: RuleStatus
    message: str
    message_ar: str
    details: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'rule_name_ar': self.rule_name_ar,
            'category': self.category,
            'status': self.status.value,
            'message': self.message,
            'message_ar': self.message_ar,
            'details': self.details or {},
        }


# ==============================================================================
# ACCOUNTING RULES VALIDATOR
# ==============================================================================

class AccountingRulesValidator:
    """
    قواعد المحاسبة الصارمة
    Deterministic accounting rules enforcement
    
    Rules:
    - ACC-001: Debit must equal Credit
    - ACC-002: No zero-value journal entries
    - ACC-003: Account codes must exist and be active
    - ACC-004: Account types must match transaction type
    """
    
    CATEGORY = "accounting"
    
    def validate_debit_equals_credit(
        self, 
        debit_amount: Decimal, 
        credit_amount: Decimal,
        entry_id: str = None
    ) -> RuleResult:
        """
        ACC-001: القيد المدين يجب أن يساوي القيد الدائن
        Debit must equal Credit
        """
        # Ensure Decimal types
        try:
            debit = Decimal(str(debit_amount))
            credit = Decimal(str(credit_amount))
        except (InvalidOperation, TypeError, ValueError):
            return RuleResult(
                rule_id="ACC-001",
                rule_name="Debit Equals Credit",
                rule_name_ar="المدين يساوي الدائن",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid amount format. Debit: {debit_amount}, Credit: {credit_amount}",
                message_ar=f"تنسيق المبلغ غير صحيح. مدين: {debit_amount}, دائن: {credit_amount}",
                details={'entry_id': entry_id, 'debit': str(debit_amount), 'credit': str(credit_amount)}
            )
        
        # Round to 2 decimal places for comparison
        debit_rounded = debit.quantize(Decimal('0.01'))
        credit_rounded = credit.quantize(Decimal('0.01'))
        
        if debit_rounded != credit_rounded:
            difference = abs(debit_rounded - credit_rounded)
            return RuleResult(
                rule_id="ACC-001",
                rule_name="Debit Equals Credit",
                rule_name_ar="المدين يساوي الدائن",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Debit ({debit_rounded}) does not equal Credit ({credit_rounded}). Difference: {difference}",
                message_ar=f"المدين ({debit_rounded}) لا يساوي الدائن ({credit_rounded}). الفرق: {difference}",
                details={
                    'entry_id': entry_id,
                    'debit': str(debit_rounded),
                    'credit': str(credit_rounded),
                    'difference': str(difference)
                }
            )
        
        return RuleResult(
            rule_id="ACC-001",
            rule_name="Debit Equals Credit",
            rule_name_ar="المدين يساوي الدائن",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Debit equals Credit: {debit_rounded}",
            message_ar=f"المدين يساوي الدائن: {debit_rounded}",
            details={'entry_id': entry_id, 'amount': str(debit_rounded)}
        )
    
    def validate_no_zero_value_entry(
        self,
        debit_amount: Decimal,
        credit_amount: Decimal,
        entry_id: str = None
    ) -> RuleResult:
        """
        ACC-002: لا يجوز وجود قيود يومية بقيمة صفر
        No zero-value journal entries allowed
        """
        try:
            debit = Decimal(str(debit_amount))
            credit = Decimal(str(credit_amount))
        except (InvalidOperation, TypeError, ValueError):
            return RuleResult(
                rule_id="ACC-002",
                rule_name="No Zero-Value Entries",
                rule_name_ar="لا قيود صفرية",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Invalid amount format",
                message_ar="تنسيق المبلغ غير صحيح",
                details={'entry_id': entry_id}
            )
        
        if debit == Decimal('0') and credit == Decimal('0'):
            return RuleResult(
                rule_id="ACC-002",
                rule_name="No Zero-Value Entries",
                rule_name_ar="لا قيود صفرية",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Zero-value journal entries are not allowed",
                message_ar="لا يُسمح بقيود يومية بقيمة صفر",
                details={'entry_id': entry_id, 'debit': str(debit), 'credit': str(credit)}
            )
        
        return RuleResult(
            rule_id="ACC-002",
            rule_name="No Zero-Value Entries",
            rule_name_ar="لا قيود صفرية",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message="Entry has non-zero value",
            message_ar="القيد له قيمة غير صفرية",
            details={'entry_id': entry_id}
        )
    
    def validate_account_exists_and_active(
        self,
        account_code: str,
        existing_accounts: Dict[str, Dict],  # {code: {active: bool, type: str}}
        entry_id: str = None
    ) -> RuleResult:
        """
        ACC-003: رمز الحساب يجب أن يكون موجوداً ونشطاً
        Account code must exist and be active
        """
        if not account_code:
            return RuleResult(
                rule_id="ACC-003",
                rule_name="Account Exists and Active",
                rule_name_ar="الحساب موجود ونشط",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Account code is missing",
                message_ar="رمز الحساب مفقود",
                details={'entry_id': entry_id, 'account_code': None}
            )
        
        if account_code not in existing_accounts:
            return RuleResult(
                rule_id="ACC-003",
                rule_name="Account Exists and Active",
                rule_name_ar="الحساب موجود ونشط",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Account code '{account_code}' does not exist",
                message_ar=f"رمز الحساب '{account_code}' غير موجود",
                details={'entry_id': entry_id, 'account_code': account_code}
            )
        
        account_info = existing_accounts[account_code]
        if not account_info.get('active', False):
            return RuleResult(
                rule_id="ACC-003",
                rule_name="Account Exists and Active",
                rule_name_ar="الحساب موجود ونشط",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Account '{account_code}' is not active",
                message_ar=f"الحساب '{account_code}' غير نشط",
                details={'entry_id': entry_id, 'account_code': account_code, 'active': False}
            )
        
        return RuleResult(
            rule_id="ACC-003",
            rule_name="Account Exists and Active",
            rule_name_ar="الحساب موجود ونشط",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Account '{account_code}' exists and is active",
            message_ar=f"الحساب '{account_code}' موجود ونشط",
            details={'entry_id': entry_id, 'account_code': account_code, 'active': True}
        )
    
    def validate_account_type_match(
        self,
        account_code: str,
        transaction_type: str,
        existing_accounts: Dict[str, Dict],
        entry_id: str = None
    ) -> RuleResult:
        """
        ACC-004: نوع الحساب يجب أن يطابق نوع المعاملة
        Account type must match transaction type
        """
        # Valid mappings: transaction_type -> allowed account types
        VALID_MAPPINGS = {
            'income': ['revenue', 'asset'],  # Income increases revenue/asset
            'expense': ['expense', 'asset'],  # Expense increases expense/reduces asset
            'asset': ['asset'],
            'liability': ['liability'],
            'equity': ['equity'],
        }
        
        if account_code not in existing_accounts:
            return RuleResult(
                rule_id="ACC-004",
                rule_name="Account Type Match",
                rule_name_ar="تطابق نوع الحساب",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Account '{account_code}' not found for type validation",
                message_ar=f"الحساب '{account_code}' غير موجود للتحقق من النوع",
                details={'entry_id': entry_id, 'account_code': account_code}
            )
        
        account_type = existing_accounts[account_code].get('type', '')
        allowed_types = VALID_MAPPINGS.get(transaction_type, [])
        
        if account_type not in allowed_types:
            return RuleResult(
                rule_id="ACC-004",
                rule_name="Account Type Match",
                rule_name_ar="تطابق نوع الحساب",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Account type '{account_type}' does not match transaction type '{transaction_type}'",
                message_ar=f"نوع الحساب '{account_type}' لا يطابق نوع المعاملة '{transaction_type}'",
                details={
                    'entry_id': entry_id,
                    'account_code': account_code,
                    'account_type': account_type,
                    'transaction_type': transaction_type,
                    'allowed_types': allowed_types
                }
            )
        
        return RuleResult(
            rule_id="ACC-004",
            rule_name="Account Type Match",
            rule_name_ar="تطابق نوع الحساب",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Account type '{account_type}' matches transaction type '{transaction_type}'",
            message_ar=f"نوع الحساب '{account_type}' يطابق نوع المعاملة '{transaction_type}'",
            details={'entry_id': entry_id, 'account_code': account_code}
        )


# ==============================================================================
# INVOICE RULES VALIDATOR
# ==============================================================================

class InvoiceRulesValidator:
    """
    قواعد الفواتير الصارمة
    Deterministic invoice rules enforcement
    
    Rules:
    - INV-001: Mandatory fields present
    - INV-002: Subtotal + VAT + Taxes = Total
    - INV-003: Invoice date must not be in the future
    - INV-004: Currency must be valid and consistent
    """
    
    CATEGORY = "invoice"
    
    # Mandatory fields for tax invoices
    MANDATORY_FIELDS = [
        ('invoice_number', 'رقم الفاتورة', 'Invoice Number'),
        ('invoice_date', 'تاريخ الفاتورة', 'Invoice Date'),
        ('party_name', 'اسم الطرف', 'Party Name'),
        ('total_amount', 'المبلغ الإجمالي', 'Total Amount'),
        ('currency', 'العملة', 'Currency'),
    ]
    
    # Valid currencies (ISO 4217)
    VALID_CURRENCIES = {
        'SAR', 'AED', 'BHD', 'KWD', 'OMR', 'QAR',  # GCC
        'USD', 'EUR', 'GBP',  # Major international
    }
    
    def validate_mandatory_fields(
        self,
        invoice_data: Dict,
        invoice_id: str = None
    ) -> RuleResult:
        """
        INV-001: الحقول الإلزامية موجودة
        All mandatory fields must be present
        """
        missing_fields = []
        missing_fields_ar = []
        
        for field_key, field_ar, field_en in self.MANDATORY_FIELDS:
            value = invoice_data.get(field_key)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field_en)
                missing_fields_ar.append(field_ar)
        
        if missing_fields:
            return RuleResult(
                rule_id="INV-001",
                rule_name="Mandatory Fields Present",
                rule_name_ar="الحقول الإلزامية موجودة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Missing mandatory fields: {', '.join(missing_fields)}",
                message_ar=f"الحقول الإلزامية المفقودة: {', '.join(missing_fields_ar)}",
                details={
                    'invoice_id': invoice_id,
                    'missing_fields': missing_fields,
                    'missing_fields_ar': missing_fields_ar
                }
            )
        
        return RuleResult(
            rule_id="INV-001",
            rule_name="Mandatory Fields Present",
            rule_name_ar="الحقول الإلزامية موجودة",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message="All mandatory fields are present",
            message_ar="جميع الحقول الإلزامية موجودة",
            details={'invoice_id': invoice_id}
        )
    
    def validate_total_calculation(
        self,
        subtotal: Decimal,
        vat_amount: Decimal,
        other_taxes: Decimal,
        total_amount: Decimal,
        invoice_id: str = None
    ) -> RuleResult:
        """
        INV-002: المجموع الفرعي + الضريبة = الإجمالي
        Subtotal + VAT + Taxes = Total
        """
        try:
            sub = Decimal(str(subtotal or 0))
            vat = Decimal(str(vat_amount or 0))
            taxes = Decimal(str(other_taxes or 0))
            total = Decimal(str(total_amount or 0))
        except (InvalidOperation, TypeError, ValueError) as e:
            return RuleResult(
                rule_id="INV-002",
                rule_name="Total Calculation",
                rule_name_ar="حساب المجموع",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid amount format: {str(e)}",
                message_ar=f"تنسيق المبلغ غير صحيح: {str(e)}",
                details={'invoice_id': invoice_id}
            )
        
        calculated_total = (sub + vat + taxes).quantize(Decimal('0.01'))
        declared_total = total.quantize(Decimal('0.01'))
        
        # Allow small rounding difference (1 cent)
        if abs(calculated_total - declared_total) > Decimal('0.01'):
            return RuleResult(
                rule_id="INV-002",
                rule_name="Total Calculation",
                rule_name_ar="حساب المجموع",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Calculated total ({calculated_total}) does not match declared total ({declared_total})",
                message_ar=f"المجموع المحسوب ({calculated_total}) لا يطابق المجموع المعلن ({declared_total})",
                details={
                    'invoice_id': invoice_id,
                    'subtotal': str(sub),
                    'vat_amount': str(vat),
                    'other_taxes': str(taxes),
                    'calculated_total': str(calculated_total),
                    'declared_total': str(declared_total),
                    'difference': str(abs(calculated_total - declared_total))
                }
            )
        
        return RuleResult(
            rule_id="INV-002",
            rule_name="Total Calculation",
            rule_name_ar="حساب المجموع",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Total calculation is correct: {declared_total}",
            message_ar=f"حساب المجموع صحيح: {declared_total}",
            details={'invoice_id': invoice_id, 'total': str(declared_total)}
        )
    
    def validate_invoice_date(
        self,
        invoice_date: Any,
        invoice_id: str = None
    ) -> RuleResult:
        """
        INV-003: تاريخ الفاتورة لا يجوز أن يكون في المستقبل
        Invoice date must not be in the future
        """
        if invoice_date is None:
            return RuleResult(
                rule_id="INV-003",
                rule_name="Invoice Date Valid",
                rule_name_ar="تاريخ الفاتورة صالح",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Invoice date is missing",
                message_ar="تاريخ الفاتورة مفقود",
                details={'invoice_id': invoice_id}
            )
        
        # Parse date if string
        if isinstance(invoice_date, str):
            try:
                invoice_date = datetime.strptime(invoice_date[:10], '%Y-%m-%d').date()
            except ValueError:
                return RuleResult(
                    rule_id="INV-003",
                    rule_name="Invoice Date Valid",
                    rule_name_ar="تاريخ الفاتورة صالح",
                    category=self.CATEGORY,
                    status=RuleStatus.FAIL,
                    message=f"Invalid date format: {invoice_date}",
                    message_ar=f"تنسيق التاريخ غير صحيح: {invoice_date}",
                    details={'invoice_id': invoice_id}
                )
        elif isinstance(invoice_date, datetime):
            invoice_date = invoice_date.date()
        
        today = date.today()
        if invoice_date > today:
            return RuleResult(
                rule_id="INV-003",
                rule_name="Invoice Date Valid",
                rule_name_ar="تاريخ الفاتورة صالح",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invoice date ({invoice_date}) cannot be in the future",
                message_ar=f"تاريخ الفاتورة ({invoice_date}) لا يمكن أن يكون في المستقبل",
                details={
                    'invoice_id': invoice_id,
                    'invoice_date': str(invoice_date),
                    'today': str(today)
                }
            )
        
        return RuleResult(
            rule_id="INV-003",
            rule_name="Invoice Date Valid",
            rule_name_ar="تاريخ الفاتورة صالح",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Invoice date ({invoice_date}) is valid",
            message_ar=f"تاريخ الفاتورة ({invoice_date}) صالح",
            details={'invoice_id': invoice_id, 'invoice_date': str(invoice_date)}
        )
    
    def validate_currency(
        self,
        currency: str,
        invoice_id: str = None
    ) -> RuleResult:
        """
        INV-004: العملة يجب أن تكون صالحة
        Currency must be valid (ISO 4217)
        """
        if not currency:
            return RuleResult(
                rule_id="INV-004",
                rule_name="Currency Valid",
                rule_name_ar="العملة صالحة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Currency is missing",
                message_ar="العملة مفقودة",
                details={'invoice_id': invoice_id}
            )
        
        currency_upper = currency.upper().strip()
        if currency_upper not in self.VALID_CURRENCIES:
            return RuleResult(
                rule_id="INV-004",
                rule_name="Currency Valid",
                rule_name_ar="العملة صالحة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid currency code: {currency}",
                message_ar=f"رمز العملة غير صالح: {currency}",
                details={
                    'invoice_id': invoice_id,
                    'currency': currency,
                    'valid_currencies': list(self.VALID_CURRENCIES)
                }
            )
        
        return RuleResult(
            rule_id="INV-004",
            rule_name="Currency Valid",
            rule_name_ar="العملة صالحة",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Currency ({currency_upper}) is valid",
            message_ar=f"العملة ({currency_upper}) صالحة",
            details={'invoice_id': invoice_id, 'currency': currency_upper}
        )


# ==============================================================================
# VAT RULES VALIDATOR
# ==============================================================================

class VATRulesValidator:
    """
    قواعد ضريبة القيمة المضافة الصارمة
    Deterministic VAT rules enforcement
    
    Rules:
    - VAT-001: VAT rate must match country regulations
    - VAT-002: VAT amount = taxable amount × VAT rate
    - VAT-003: Zero or exempt VAT must have legal justification
    """
    
    CATEGORY = "vat"
    
    # Country VAT rates (as of 2024)
    COUNTRY_VAT_RATES = {
        'SA': Decimal('15.00'),  # Saudi Arabia - 15%
        'AE': Decimal('5.00'),   # UAE - 5%
        'BH': Decimal('10.00'),  # Bahrain - 10%
        'OM': Decimal('5.00'),   # Oman - 5%
        'KW': Decimal('0.00'),   # Kuwait - No VAT
        'QA': Decimal('0.00'),   # Qatar - No VAT
    }
    
    # Valid VAT exemption codes
    EXEMPTION_CODES = {
        'VATEX-SA-29',     # Zero-rated supplies
        'VATEX-SA-29-7',   # Exports
        'VATEX-SA-30',     # Exempt supplies
        'VATEX-SA-32',     # Financial services
        'VATEX-SA-33',     # Life insurance
        'VATEX-SA-34-1',   # Real estate (residential)
        'VATEX-SA-34-2',   # Real estate (first sale)
        'VATEX-SA-35',     # Qualifying metals
        'VATEX-SA-36',     # Private education
        'VATEX-SA-EDU',    # Education
        'VATEX-SA-HEA',    # Healthcare
    }
    
    def validate_vat_rate(
        self,
        declared_rate: Decimal,
        country: str,
        invoice_id: str = None
    ) -> RuleResult:
        """
        VAT-001: نسبة الضريبة يجب أن تطابق الأنظمة
        VAT rate must match country regulations
        """
        try:
            rate = Decimal(str(declared_rate or 0))
        except (InvalidOperation, TypeError, ValueError):
            return RuleResult(
                rule_id="VAT-001",
                rule_name="VAT Rate Match",
                rule_name_ar="مطابقة نسبة الضريبة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid VAT rate format: {declared_rate}",
                message_ar=f"تنسيق نسبة الضريبة غير صحيح: {declared_rate}",
                details={'invoice_id': invoice_id}
            )
        
        country_upper = country.upper() if country else ''
        expected_rate = self.COUNTRY_VAT_RATES.get(country_upper, None)
        
        if expected_rate is None:
            return RuleResult(
                rule_id="VAT-001",
                rule_name="VAT Rate Match",
                rule_name_ar="مطابقة نسبة الضريبة",
                category=self.CATEGORY,
                status=RuleStatus.WARNING,
                message=f"Country '{country}' VAT rate not configured",
                message_ar=f"نسبة الضريبة للدولة '{country}' غير مُعدة",
                details={'invoice_id': invoice_id, 'country': country}
            )
        
        # Allow 0% for exempt/zero-rated, or the standard rate
        if rate != Decimal('0') and rate != expected_rate:
            return RuleResult(
                rule_id="VAT-001",
                rule_name="VAT Rate Match",
                rule_name_ar="مطابقة نسبة الضريبة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"VAT rate ({rate}%) does not match {country} rate ({expected_rate}%)",
                message_ar=f"نسبة الضريبة ({rate}%) لا تطابق نسبة {country} ({expected_rate}%)",
                details={
                    'invoice_id': invoice_id,
                    'declared_rate': str(rate),
                    'expected_rate': str(expected_rate),
                    'country': country
                }
            )
        
        return RuleResult(
            rule_id="VAT-001",
            rule_name="VAT Rate Match",
            rule_name_ar="مطابقة نسبة الضريبة",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"VAT rate ({rate}%) is valid for {country}",
            message_ar=f"نسبة الضريبة ({rate}%) صالحة لـ {country}",
            details={'invoice_id': invoice_id, 'rate': str(rate), 'country': country}
        )
    
    def validate_vat_calculation(
        self,
        taxable_amount: Decimal,
        vat_rate: Decimal,
        declared_vat: Decimal,
        invoice_id: str = None
    ) -> RuleResult:
        """
        VAT-002: مبلغ الضريبة = المبلغ الخاضع × نسبة الضريبة
        VAT amount must equal taxable amount × VAT rate
        """
        try:
            taxable = Decimal(str(taxable_amount or 0))
            rate = Decimal(str(vat_rate or 0))
            declared = Decimal(str(declared_vat or 0))
        except (InvalidOperation, TypeError, ValueError) as e:
            return RuleResult(
                rule_id="VAT-002",
                rule_name="VAT Calculation",
                rule_name_ar="حساب الضريبة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid amount format: {str(e)}",
                message_ar=f"تنسيق المبلغ غير صحيح: {str(e)}",
                details={'invoice_id': invoice_id}
            )
        
        # Calculate expected VAT
        expected_vat = (taxable * rate / Decimal('100')).quantize(Decimal('0.01'))
        declared_vat_rounded = declared.quantize(Decimal('0.01'))
        
        # Allow 1 cent tolerance for rounding
        if abs(expected_vat - declared_vat_rounded) > Decimal('0.01'):
            return RuleResult(
                rule_id="VAT-002",
                rule_name="VAT Calculation",
                rule_name_ar="حساب الضريبة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Calculated VAT ({expected_vat}) does not match declared VAT ({declared_vat_rounded})",
                message_ar=f"الضريبة المحسوبة ({expected_vat}) لا تطابق الضريبة المعلنة ({declared_vat_rounded})",
                details={
                    'invoice_id': invoice_id,
                    'taxable_amount': str(taxable),
                    'vat_rate': str(rate),
                    'expected_vat': str(expected_vat),
                    'declared_vat': str(declared_vat_rounded),
                    'difference': str(abs(expected_vat - declared_vat_rounded))
                }
            )
        
        return RuleResult(
            rule_id="VAT-002",
            rule_name="VAT Calculation",
            rule_name_ar="حساب الضريبة",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"VAT calculation is correct: {declared_vat_rounded}",
            message_ar=f"حساب الضريبة صحيح: {declared_vat_rounded}",
            details={'invoice_id': invoice_id, 'vat_amount': str(declared_vat_rounded)}
        )
    
    def validate_zero_vat_justification(
        self,
        vat_amount: Decimal,
        exemption_code: str,
        exemption_reason: str,
        invoice_id: str = None
    ) -> RuleResult:
        """
        VAT-003: الضريبة الصفرية أو المعفاة يجب أن يكون لها مبرر قانوني
        Zero or exempt VAT must have legal justification
        """
        try:
            vat = Decimal(str(vat_amount or 0))
        except (InvalidOperation, TypeError, ValueError):
            vat = Decimal('0')
        
        # If VAT is not zero, this rule doesn't apply
        if vat != Decimal('0'):
            return RuleResult(
                rule_id="VAT-003",
                rule_name="Zero VAT Justification",
                rule_name_ar="مبرر الضريبة الصفرية",
                category=self.CATEGORY,
                status=RuleStatus.PASS,
                message="Non-zero VAT - justification not required",
                message_ar="ضريبة غير صفرية - المبرر غير مطلوب",
                details={'invoice_id': invoice_id, 'vat_amount': str(vat)}
            )
        
        # Zero VAT requires justification
        if not exemption_code and not exemption_reason:
            return RuleResult(
                rule_id="VAT-003",
                rule_name="Zero VAT Justification",
                rule_name_ar="مبرر الضريبة الصفرية",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Zero VAT requires exemption code or reason",
                message_ar="الضريبة الصفرية تتطلب رمز إعفاء أو سبب",
                details={'invoice_id': invoice_id}
            )
        
        # Validate exemption code if provided
        if exemption_code and exemption_code not in self.EXEMPTION_CODES:
            return RuleResult(
                rule_id="VAT-003",
                rule_name="Zero VAT Justification",
                rule_name_ar="مبرر الضريبة الصفرية",
                category=self.CATEGORY,
                status=RuleStatus.WARNING,
                message=f"Unknown exemption code: {exemption_code}",
                message_ar=f"رمز إعفاء غير معروف: {exemption_code}",
                details={
                    'invoice_id': invoice_id,
                    'exemption_code': exemption_code,
                    'valid_codes': list(self.EXEMPTION_CODES)
                }
            )
        
        return RuleResult(
            rule_id="VAT-003",
            rule_name="Zero VAT Justification",
            rule_name_ar="مبرر الضريبة الصفرية",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Zero VAT justified: {exemption_code or exemption_reason[:50]}",
            message_ar=f"الضريبة الصفرية مبررة: {exemption_code or exemption_reason[:50]}",
            details={
                'invoice_id': invoice_id,
                'exemption_code': exemption_code,
                'exemption_reason': exemption_reason
            }
        )


# ==============================================================================
# COMPLIANCE RULES VALIDATOR (ZATCA / GCC)
# ==============================================================================

class ComplianceRulesValidator:
    """
    قواعد الامتثال الصارمة (ZATCA / GCC)
    Deterministic compliance rules enforcement
    
    Rules:
    - CMP-001: UUID present and valid
    - CMP-002: QR Code present
    - CMP-003: Invoice schema valid
    - CMP-004: Invoice numbering unique
    - CMP-005: Valid invoice type
    """
    
    CATEGORY = "compliance"
    
    # Valid invoice types (ZATCA)
    VALID_INVOICE_TYPES = {
        '388': 'فاتورة ضريبية - Tax Invoice',
        '381': 'إشعار دائن - Credit Note',
        '383': 'إشعار مدين - Debit Note',
    }
    
    # Saudi VAT number pattern: 3 + 13 digits + 3
    SAUDI_VAT_PATTERN = r'^3\d{13}3$'
    
    def validate_uuid_present(
        self,
        invoice_uuid: str,
        invoice_id: str = None
    ) -> RuleResult:
        """
        CMP-001: المعرف الفريد موجود وصالح
        UUID must be present and valid format
        """
        if not invoice_uuid:
            return RuleResult(
                rule_id="CMP-001",
                rule_name="UUID Present",
                rule_name_ar="المعرف الفريد موجود",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Invoice UUID is missing",
                message_ar="المعرف الفريد للفاتورة مفقود",
                details={'invoice_id': invoice_id}
            )
        
        # Validate UUID format
        try:
            uuid_module.UUID(str(invoice_uuid))
        except (ValueError, AttributeError):
            return RuleResult(
                rule_id="CMP-001",
                rule_name="UUID Present",
                rule_name_ar="المعرف الفريد موجود",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid UUID format: {invoice_uuid}",
                message_ar=f"تنسيق المعرف الفريد غير صحيح: {invoice_uuid}",
                details={'invoice_id': invoice_id, 'uuid': str(invoice_uuid)}
            )
        
        return RuleResult(
            rule_id="CMP-001",
            rule_name="UUID Present",
            rule_name_ar="المعرف الفريد موجود",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"UUID is valid: {invoice_uuid}",
            message_ar=f"المعرف الفريد صالح: {invoice_uuid}",
            details={'invoice_id': invoice_id, 'uuid': str(invoice_uuid)}
        )
    
    def validate_qr_code_present(
        self,
        qr_code: str,
        invoice_subtype: str = '0100000',
        invoice_id: str = None
    ) -> RuleResult:
        """
        CMP-002: رمز QR موجود
        QR Code must be present (required for simplified invoices)
        """
        # QR code is mandatory for simplified invoices (0200000)
        is_simplified = invoice_subtype == '0200000'
        
        if not qr_code:
            if is_simplified:
                return RuleResult(
                    rule_id="CMP-002",
                    rule_name="QR Code Present",
                    rule_name_ar="رمز QR موجود",
                    category=self.CATEGORY,
                    status=RuleStatus.FAIL,
                    message="QR Code is mandatory for simplified invoices",
                    message_ar="رمز QR إلزامي للفواتير المبسطة",
                    details={'invoice_id': invoice_id, 'invoice_subtype': invoice_subtype}
                )
            else:
                return RuleResult(
                    rule_id="CMP-002",
                    rule_name="QR Code Present",
                    rule_name_ar="رمز QR موجود",
                    category=self.CATEGORY,
                    status=RuleStatus.WARNING,
                    message="QR Code not present (recommended for standard invoices)",
                    message_ar="رمز QR غير موجود (موصى به للفواتير القياسية)",
                    details={'invoice_id': invoice_id, 'invoice_subtype': invoice_subtype}
                )
        
        return RuleResult(
            rule_id="CMP-002",
            rule_name="QR Code Present",
            rule_name_ar="رمز QR موجود",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message="QR Code is present",
            message_ar="رمز QR موجود",
            details={'invoice_id': invoice_id, 'qr_length': len(qr_code)}
        )
    
    def validate_invoice_schema(
        self,
        invoice_data: Dict,
        invoice_id: str = None
    ) -> RuleResult:
        """
        CMP-003: مخطط الفاتورة صالح
        Invoice schema must be valid
        """
        schema_errors = []
        
        # Required fields for ZATCA schema
        required_fields = [
            ('invoice_number', 'رقم الفاتورة'),
            ('uuid', 'المعرف الفريد'),
            ('issue_date', 'تاريخ الإصدار'),
            ('seller_name', 'اسم البائع'),
            ('seller_vat_number', 'الرقم الضريبي للبائع'),
            ('total_including_vat', 'المجموع شامل الضريبة'),
        ]
        
        for field_key, field_ar in required_fields:
            if field_key not in invoice_data or not invoice_data[field_key]:
                schema_errors.append(f"{field_key} ({field_ar})")
        
        # Validate VAT number format for seller
        seller_vat = invoice_data.get('seller_vat_number', '')
        if seller_vat and not re.match(self.SAUDI_VAT_PATTERN, str(seller_vat)):
            schema_errors.append("seller_vat_number format invalid")
        
        if schema_errors:
            return RuleResult(
                rule_id="CMP-003",
                rule_name="Invoice Schema Valid",
                rule_name_ar="مخطط الفاتورة صالح",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Schema validation failed: {', '.join(schema_errors)}",
                message_ar=f"فشل التحقق من المخطط: {', '.join(schema_errors)}",
                details={'invoice_id': invoice_id, 'errors': schema_errors}
            )
        
        return RuleResult(
            rule_id="CMP-003",
            rule_name="Invoice Schema Valid",
            rule_name_ar="مخطط الفاتورة صالح",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message="Invoice schema is valid",
            message_ar="مخطط الفاتورة صالح",
            details={'invoice_id': invoice_id}
        )
    
    def validate_invoice_number_unique(
        self,
        invoice_number: str,
        organization_id: str,
        existing_numbers: set,
        invoice_id: str = None
    ) -> RuleResult:
        """
        CMP-004: ترقيم الفاتورة فريد
        Invoice numbering must be unique
        """
        if not invoice_number:
            return RuleResult(
                rule_id="CMP-004",
                rule_name="Invoice Number Unique",
                rule_name_ar="ترقيم الفاتورة فريد",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Invoice number is missing",
                message_ar="رقم الفاتورة مفقود",
                details={'invoice_id': invoice_id}
            )
        
        if invoice_number in existing_numbers:
            return RuleResult(
                rule_id="CMP-004",
                rule_name="Invoice Number Unique",
                rule_name_ar="ترقيم الفاتورة فريد",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invoice number '{invoice_number}' already exists",
                message_ar=f"رقم الفاتورة '{invoice_number}' موجود مسبقاً",
                details={
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    'organization_id': organization_id
                }
            )
        
        return RuleResult(
            rule_id="CMP-004",
            rule_name="Invoice Number Unique",
            rule_name_ar="ترقيم الفاتورة فريد",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Invoice number '{invoice_number}' is unique",
            message_ar=f"رقم الفاتورة '{invoice_number}' فريد",
            details={'invoice_id': invoice_id, 'invoice_number': invoice_number}
        )
    
    def validate_invoice_type(
        self,
        invoice_type_code: str,
        invoice_id: str = None
    ) -> RuleResult:
        """
        CMP-005: نوع الفاتورة صالح
        Invoice type must be valid (Tax / Simplified / Credit Note)
        """
        if not invoice_type_code:
            return RuleResult(
                rule_id="CMP-005",
                rule_name="Invoice Type Valid",
                rule_name_ar="نوع الفاتورة صالح",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Invoice type code is missing",
                message_ar="رمز نوع الفاتورة مفقود",
                details={'invoice_id': invoice_id}
            )
        
        if invoice_type_code not in self.VALID_INVOICE_TYPES:
            return RuleResult(
                rule_id="CMP-005",
                rule_name="Invoice Type Valid",
                rule_name_ar="نوع الفاتورة صالح",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"Invalid invoice type code: {invoice_type_code}",
                message_ar=f"رمز نوع الفاتورة غير صالح: {invoice_type_code}",
                details={
                    'invoice_id': invoice_id,
                    'invoice_type_code': invoice_type_code,
                    'valid_types': self.VALID_INVOICE_TYPES
                }
            )
        
        type_name = self.VALID_INVOICE_TYPES[invoice_type_code]
        return RuleResult(
            rule_id="CMP-005",
            rule_name="Invoice Type Valid",
            rule_name_ar="نوع الفاتورة صالح",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Invoice type is valid: {type_name}",
            message_ar=f"نوع الفاتورة صالح: {type_name}",
            details={'invoice_id': invoice_id, 'invoice_type': type_name}
        )


# ==============================================================================
# OCR CONFIDENCE RULES VALIDATOR
# ==============================================================================

class OCRConfidenceValidator:
    """
    قواعد ثقة التعرف الضوئي الصارمة
    Deterministic OCR confidence rules enforcement
    
    Rules:
    - OCR-001: Critical numeric fields with confidence < 85% require human review
    """
    
    CATEGORY = "ocr"
    
    # Minimum confidence threshold for critical fields
    CRITICAL_CONFIDENCE_THRESHOLD = 85
    
    # Critical numeric fields that require high confidence
    CRITICAL_FIELDS = [
        'total_amount',
        'vat_amount',
        'invoice_number',
        'vat_number',
    ]
    
    def validate_ocr_confidence(
        self,
        field_name: str,
        field_value: Any,
        confidence_score: int,
        document_id: str = None
    ) -> RuleResult:
        """
        OCR-001: الحقول الرقمية الحرجة بثقة < 85% تتطلب مراجعة بشرية
        Critical numeric fields with confidence < 85% must require human review
        """
        # Skip non-critical fields
        if field_name not in self.CRITICAL_FIELDS:
            return RuleResult(
                rule_id="OCR-001",
                rule_name="OCR Confidence Check",
                rule_name_ar="فحص ثقة التعرف الضوئي",
                category=self.CATEGORY,
                status=RuleStatus.PASS,
                message=f"Field '{field_name}' is not critical - no confidence check required",
                message_ar=f"الحقل '{field_name}' ليس حرجاً - لا يتطلب فحص الثقة",
                details={'document_id': document_id, 'field_name': field_name}
            )
        
        # Check confidence score
        try:
            score = int(confidence_score)
        except (TypeError, ValueError):
            score = 0
        
        if score < self.CRITICAL_CONFIDENCE_THRESHOLD:
            return RuleResult(
                rule_id="OCR-001",
                rule_name="OCR Confidence Check",
                rule_name_ar="فحص ثقة التعرف الضوئي",
                category=self.CATEGORY,
                status=RuleStatus.BLOCKED,
                message=f"Field '{field_name}' has low confidence ({score}%) - REQUIRES HUMAN REVIEW",
                message_ar=f"الحقل '{field_name}' له ثقة منخفضة ({score}%) - يتطلب مراجعة بشرية",
                details={
                    'document_id': document_id,
                    'field_name': field_name,
                    'field_value': str(field_value),
                    'confidence_score': score,
                    'threshold': self.CRITICAL_CONFIDENCE_THRESHOLD,
                    'requires_human_review': True
                }
            )
        
        return RuleResult(
            rule_id="OCR-001",
            rule_name="OCR Confidence Check",
            rule_name_ar="فحص ثقة التعرف الضوئي",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Field '{field_name}' confidence ({score}%) meets threshold",
            message_ar=f"ثقة الحقل '{field_name}' ({score}%) تلبي الحد الأدنى",
            details={
                'document_id': document_id,
                'field_name': field_name,
                'confidence_score': score
            }
        )
    
    def validate_document_confidence(
        self,
        extracted_data: Dict,
        field_confidences: Dict[str, int],
        document_id: str = None
    ) -> List[RuleResult]:
        """
        Validate all critical fields in a document for confidence
        """
        results = []
        
        for field_name in self.CRITICAL_FIELDS:
            if field_name in extracted_data:
                confidence = field_confidences.get(field_name, 0)
                result = self.validate_ocr_confidence(
                    field_name=field_name,
                    field_value=extracted_data.get(field_name),
                    confidence_score=confidence,
                    document_id=document_id
                )
                results.append(result)
        
        return results


# ==============================================================================
# SECURITY & AUDIT RULES VALIDATOR
# ==============================================================================

class SecurityAuditValidator:
    """
    قواعد الأمان والتدقيق الصارمة
    Deterministic security and audit rules enforcement
    
    Rules:
    - SEC-001: User permissions validated
    - SEC-002: Creator ≠ Approver (segregation of duties)
    - SEC-003: Full audit trail exists
    """
    
    CATEGORY = "security"
    
    # Role hierarchy for permission checks
    ROLE_PERMISSIONS = {
        'user': ['view'],
        'auditor': ['view', 'audit', 'report'],
        'accountant': ['view', 'create', 'edit'],
        'finance_manager': ['view', 'create', 'edit', 'approve'],
        'admin': ['view', 'create', 'edit', 'approve', 'delete', 'admin'],
    }
    
    def validate_user_permission(
        self,
        user_role: str,
        required_permission: str,
        user_id: str = None,
        resource_id: str = None
    ) -> RuleResult:
        """
        SEC-001: صلاحيات المستخدم مُحققة
        User must have required permission
        """
        if not user_role:
            return RuleResult(
                rule_id="SEC-001",
                rule_name="User Permission Valid",
                rule_name_ar="صلاحيات المستخدم صالحة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="User role is not defined",
                message_ar="دور المستخدم غير محدد",
                details={'user_id': user_id, 'resource_id': resource_id}
            )
        
        role_lower = user_role.lower()
        permissions = self.ROLE_PERMISSIONS.get(role_lower, [])
        
        if required_permission not in permissions:
            return RuleResult(
                rule_id="SEC-001",
                rule_name="User Permission Valid",
                rule_name_ar="صلاحيات المستخدم صالحة",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"User role '{user_role}' does not have '{required_permission}' permission",
                message_ar=f"دور المستخدم '{user_role}' لا يملك صلاحية '{required_permission}'",
                details={
                    'user_id': user_id,
                    'user_role': user_role,
                    'required_permission': required_permission,
                    'available_permissions': permissions
                }
            )
        
        return RuleResult(
            rule_id="SEC-001",
            rule_name="User Permission Valid",
            rule_name_ar="صلاحيات المستخدم صالحة",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"User has '{required_permission}' permission",
            message_ar=f"المستخدم يملك صلاحية '{required_permission}'",
            details={'user_id': user_id, 'permission': required_permission}
        )
    
    def validate_segregation_of_duties(
        self,
        creator_id: str,
        approver_id: str,
        entity_type: str = None,
        entity_id: str = None
    ) -> RuleResult:
        """
        SEC-002: المنشئ ≠ المعتمد (فصل المهام)
        Creator must not be the same as Approver
        """
        if not creator_id or not approver_id:
            return RuleResult(
                rule_id="SEC-002",
                rule_name="Segregation of Duties",
                rule_name_ar="فصل المهام",
                category=self.CATEGORY,
                status=RuleStatus.WARNING,
                message="Creator or Approver not specified",
                message_ar="المنشئ أو المعتمد غير محدد",
                details={'entity_type': entity_type, 'entity_id': entity_id}
            )
        
        if str(creator_id) == str(approver_id):
            return RuleResult(
                rule_id="SEC-002",
                rule_name="Segregation of Duties",
                rule_name_ar="فصل المهام",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message="Creator and Approver cannot be the same person",
                message_ar="المنشئ والمعتمد لا يمكن أن يكونا نفس الشخص",
                details={
                    'creator_id': creator_id,
                    'approver_id': approver_id,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'violation': 'segregation_of_duties'
                }
            )
        
        return RuleResult(
            rule_id="SEC-002",
            rule_name="Segregation of Duties",
            rule_name_ar="فصل المهام",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message="Creator and Approver are different users",
            message_ar="المنشئ والمعتمد مستخدمون مختلفون",
            details={
                'creator_id': creator_id,
                'approver_id': approver_id,
                'entity_type': entity_type
            }
        )
    
    def validate_audit_trail(
        self,
        entity_type: str,
        entity_id: str,
        audit_records: List[Dict],
        required_actions: List[str] = None
    ) -> RuleResult:
        """
        SEC-003: سجل التدقيق الكامل موجود
        Full audit trail must exist for all changes
        """
        if required_actions is None:
            required_actions = ['create']
        
        if not audit_records:
            return RuleResult(
                rule_id="SEC-003",
                rule_name="Audit Trail Exists",
                rule_name_ar="سجل التدقيق موجود",
                category=self.CATEGORY,
                status=RuleStatus.FAIL,
                message=f"No audit trail found for {entity_type} {entity_id}",
                message_ar=f"لا يوجد سجل تدقيق لـ {entity_type} {entity_id}",
                details={'entity_type': entity_type, 'entity_id': entity_id}
            )
        
        # Check for required actions in audit trail
        recorded_actions = {r.get('action') for r in audit_records}
        missing_actions = set(required_actions) - recorded_actions
        
        if missing_actions:
            return RuleResult(
                rule_id="SEC-003",
                rule_name="Audit Trail Exists",
                rule_name_ar="سجل التدقيق موجود",
                category=self.CATEGORY,
                status=RuleStatus.WARNING,
                message=f"Audit trail incomplete - missing actions: {', '.join(missing_actions)}",
                message_ar=f"سجل التدقيق غير مكتمل - إجراءات مفقودة: {', '.join(missing_actions)}",
                details={
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'missing_actions': list(missing_actions)
                }
            )
        
        return RuleResult(
            rule_id="SEC-003",
            rule_name="Audit Trail Exists",
            rule_name_ar="سجل التدقيق موجود",
            category=self.CATEGORY,
            status=RuleStatus.PASS,
            message=f"Audit trail complete with {len(audit_records)} records",
            message_ar=f"سجل التدقيق مكتمل مع {len(audit_records)} سجل",
            details={
                'entity_type': entity_type,
                'entity_id': entity_id,
                'record_count': len(audit_records)
            }
        )
