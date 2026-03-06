# Invoice Compliance Service
# Performs 9+ compliance checks on invoices
# Returns structured check results for audit trail

from decimal import Decimal
from typing import Dict, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)


class ComplianceCheck:
    """Represents a single compliance check result."""
    
    CHECK_AVAILABLE = "AVAILABLE"
    CHECK_MISSING = "MISSING"
    CHECK_INVALID = "INVALID"
    CHECK_PASS = "PASS"
    CHECK_WARNING = "WARNING"
    
    SEVERITY_INFO = "INFO"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_ERROR = "ERROR"
    SEVERITY_CRITICAL = "CRITICAL"
    
    def __init__(self, check_name: str, status: str, severity: str, message: str):
        self.check_name = check_name
        self.status = status
        self.severity = severity
        self.message = message
    
    def to_dict(self) -> dict:
        return {
            "check_name": self.check_name,
            "status": self.status,
            "severity": self.severity,
            "message": self.message
        }


class InvoiceComplianceService:
    """Performs compliance checks on normalized invoice data."""
    
    def __init__(self):
        self.checks_performed = []
    
    def check_invoice_compliance(self, normalized_data: dict) -> Tuple[List[ComplianceCheck], bool]:
        """
        Run all compliance checks on invoice.
        
        Returns: (list of ComplianceCheck, all_critical_checks_pass)
        """
        self.checks_performed = []
        
        # Critical checks (must pass)
        self._check_invoice_number(normalized_data)
        self._check_vendor_presence(normalized_data)
        self._check_customer_presence(normalized_data)
        self._check_items_existence(normalized_data)
        self._check_total_consistency(normalized_data)
        
        # Important checks (should pass)
        self._check_vat_tin(normalized_data)
        self._check_due_date_logic(normalized_data)
        self._check_currency_validity(normalized_data)
        
        # Risk-based checks
        self._check_suspicious_discount(normalized_data)
        
        # Determine if all critical checks pass
        critical_checks = ["invoice_number", "vendor_presence", "customer_presence", 
                          "items_existence", "total_consistency"]
        critical_pass = all(
            c.severity != ComplianceCheck.SEVERITY_CRITICAL 
            for c in self.checks_performed 
            if c.check_name in critical_checks
        )
        
        return self.checks_performed, critical_pass
    
    def _check_invoice_number(self, data: dict) -> None:
        """Check 1: Invoice number presence and format."""
        check_name = "invoice_number"
        invoice_number = data.get("invoice_number", "").strip()
        
        if not invoice_number:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message="Invoice number is missing or empty"
            )
        elif len(invoice_number) > 50:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_INVALID,
                severity=ComplianceCheck.SEVERITY_WARNING,
                message=f"Invoice number is unusually long ({len(invoice_number)} chars)"
            )
        else:
            # Check format (alphanumeric, dashes, slashes common)
            if re.match(r'^[A-Za-z0-9\-\/\s]{1,50}$', invoice_number):
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message=f"Invoice number '{invoice_number}' is valid"
                )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_INVALID,
                    severity=ComplianceCheck.SEVERITY_WARNING,
                    message=f"Invoice number contains unusual characters: {invoice_number}"
                )
        
        self.checks_performed.append(check)
    
    def _check_vendor_presence(self, data: dict) -> None:
        """Check 2: Vendor (seller) information completeness."""
        check_name = "vendor_presence"
        vendor = data.get("vendor") or {}
        vendor_name = vendor.get("name", "").strip()
        
        if not vendor_name:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message="Vendor name is missing"
            )
        else:
            # Check TIN/TAX ID if present
            vendor_tin = vendor.get("tax_id", "").strip()
            if not vendor_tin:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_AVAILABLE,
                    severity=ComplianceCheck.SEVERITY_WARNING,
                    message=f"Vendor '{vendor_name}' present but no TAX ID found"
                )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message=f"Vendor '{vendor_name}' with TAX ID present"
                )
        
        self.checks_performed.append(check)
    
    def _check_customer_presence(self, data: dict) -> None:
        """Check 3: Customer (buyer) information completeness."""
        check_name = "customer_presence"
        customer = data.get("customer") or {}
        customer_name = customer.get("name", "").strip()
        
        if not customer_name:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message="Customer name is missing"
            )
        else:
            # Check TIN/TAX ID if present
            customer_tin = customer.get("tax_id", "").strip()
            if not customer_tin:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_AVAILABLE,
                    severity=ComplianceCheck.SEVERITY_WARNING,
                    message=f"Customer '{customer_name}' present but no TAX ID found"
                )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message=f"Customer '{customer_name}' with TAX ID present"
                )
        
        self.checks_performed.append(check)
    
    def _check_items_existence(self, data: dict) -> None:
        """Check 4: Line items existence and non-empty."""
        check_name = "items_existence"
        items = data.get("items", [])
        
        if not items or len(items) == 0:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message="Invoice has no line items"
            )
        elif len(items) > 1000:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_WARNING,
                severity=ComplianceCheck.SEVERITY_WARNING,
                message=f"Invoice has {len(items)} items (unusually large)"
            )
        else:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_PASS,
                severity=ComplianceCheck.SEVERITY_INFO,
                message=f"Invoice has {len(items)} line item(s)"
            )
        
        self.checks_performed.append(check)
    
    def _check_total_consistency(self, data: dict) -> None:
        """Check 5: Invoice total matches sum of items."""
        check_name = "total_consistency"
        items = data.get("items", [])
        invoice_total = self._safe_decimal(data.get("total_amount"))
        
        if not items or invoice_total is None:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message="Cannot verify total: missing items or total amount"
            )
        else:
            # Calculate sum of line items
            lines_total = Decimal('0')
            for item in items:
                item_amount = self._safe_decimal(item.get("amount"))
                if item_amount is not None:
                    lines_total += item_amount
            
            # Compare with tolerance (0.01)
            difference = abs(invoice_total - lines_total)
            if difference <= Decimal('0.01'):
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message=f"Total {invoice_total} matches line items sum {lines_total}"
                )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_INVALID,
                    severity=ComplianceCheck.SEVERITY_CRITICAL,
                    message=f"Total mismatch: invoice {invoice_total} vs items {lines_total} (diff: {difference})"
                )
        
        self.checks_performed.append(check)
    
    def _check_vat_tin(self, data: dict) -> None:
        """Check 6: VAT/TIN presence in vendor and customer."""
        check_name = "vat_tin_check"
        vendor = data.get("vendor") or {}
        customer = data.get("customer") or {}
        
        vendor_tin = vendor.get("tax_id", "").strip()
        customer_tin = customer.get("tax_id", "").strip()
        
        missing_count = 0
        if not vendor_tin:
            missing_count += 1
        if not customer_tin:
            missing_count += 1
        
        if missing_count == 2:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_ERROR,
                message="Both vendor and customer TAX IDs are missing"
            )
        elif missing_count == 1:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_AVAILABLE,
                severity=ComplianceCheck.SEVERITY_WARNING,
                message="One party (vendor or customer) TAX ID is missing"
            )
        else:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_PASS,
                severity=ComplianceCheck.SEVERITY_INFO,
                message="Both vendor and customer TAX IDs present"
            )
        
        self.checks_performed.append(check)
    
    def _check_due_date_logic(self, data: dict) -> None:
        """Check 7: Due date is after issue date and within reasonable bounds."""
        check_name = "due_date_logic"
        issue_date = data.get("issue_date")
        due_date = data.get("due_date")
        
        if not due_date:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_WARNING,
                message="No due date specified (using net payment terms)"
            )
        elif not issue_date:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_INVALID,
                severity=ComplianceCheck.SEVERITY_ERROR,
                message="Cannot validate due date: issue date missing"
            )
        elif due_date < issue_date:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_INVALID,
                severity=ComplianceCheck.SEVERITY_CRITICAL,
                message=f"Due date {due_date} is before issue date {issue_date}"
            )
        elif due_date > issue_date:
            days_diff = (due_date.date() if hasattr(due_date, 'date') else due_date) - \
                       (issue_date.date() if hasattr(issue_date, 'date') else issue_date)
            days_diff = days_diff.days if hasattr(days_diff, 'days') else 0
            
            if days_diff > 365:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_WARNING,
                    severity=ComplianceCheck.SEVERITY_WARNING,
                    message=f"Due date is {days_diff} days away (>1 year, unusual)"
                )
            elif days_diff > 180:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_WARNING,
                    severity=ComplianceCheck.SEVERITY_WARNING,
                    message=f"Due date is {days_diff} days away (close to 6 months)"
                )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message=f"Due date is {days_diff} days after issue date (valid)"
                )
        else:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_PASS,
                severity=ComplianceCheck.SEVERITY_INFO,
                message="Due date is valid"
            )
        
        self.checks_performed.append(check)
    
    def _check_currency_validity(self, data: dict) -> None:
        """Check 8: Currency is valid ISO 4217 code."""
        check_name = "currency_validity"
        currency = data.get("currency", "").strip()
        
        # Common ISO 4217 codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
            'CNY', 'INR', 'MXN', 'BRL', 'ZAR', 'SG', 'HK', 'AED', 
            'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'ILS', 'TRY',
            'RUB', 'KRW', 'SEK', 'NOK', 'DKK', 'CZK', 'HUF', 'PLN'
        }
        
        if not currency:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_ERROR,
                message="Currency is missing"
            )
        elif currency.upper() in valid_currencies:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_PASS,
                severity=ComplianceCheck.SEVERITY_INFO,
                message=f"Currency '{currency}' is valid ISO 4217 code"
            )
        else:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_INVALID,
                severity=ComplianceCheck.SEVERITY_WARNING,
                message=f"Currency '{currency}' not recognized as standard ISO 4217 code"
            )
        
        self.checks_performed.append(check)
    
    def _check_suspicious_discount(self, data: dict) -> None:
        """Check 9: Detect unusually large discounts (fraud risk)."""
        check_name = "suspicious_discount"
        items = data.get("items", [])
        
        if not items:
            check = ComplianceCheck(
                check_name=check_name,
                status=ComplianceCheck.CHECK_MISSING,
                severity=ComplianceCheck.SEVERITY_INFO,
                message="Cannot check discounts: no items"
            )
        else:
            max_discount_percent = 0
            has_discount_line = False
            
            for item in items:
                unit_price = self._safe_decimal(item.get("unit_price"))
                amount = self._safe_decimal(item.get("amount"))
                quantity = self._safe_decimal(item.get("quantity"))
                
                if unit_price and amount and quantity and unit_price > 0:
                    expected_total = unit_price * quantity
                    if expected_total > amount:
                        discount = expected_total - amount
                        discount_percent = (discount / expected_total) * 100
                        if discount_percent > 5:  # >5% discount
                            has_discount_line = True
                            max_discount_percent = max(max_discount_percent, discount_percent)
            
            if has_discount_line:
                if max_discount_percent > 50:
                    check = ComplianceCheck(
                        check_name=check_name,
                        status=ComplianceCheck.CHECK_WARNING,
                        severity=ComplianceCheck.SEVERITY_CRITICAL,
                        message=f"Suspicious discount detected: {max_discount_percent:.1f}% (>50%)"
                    )
                elif max_discount_percent > 25:
                    check = ComplianceCheck(
                        check_name=check_name,
                        status=ComplianceCheck.CHECK_WARNING,
                        severity=ComplianceCheck.SEVERITY_WARNING,
                        message=f"Large discount detected: {max_discount_percent:.1f}% (>25%)"
                    )
                else:
                    check = ComplianceCheck(
                        check_name=check_name,
                        status=ComplianceCheck.CHECK_WARNING,
                        severity=ComplianceCheck.SEVERITY_INFO,
                        message=f"Discount detected: {max_discount_percent:.1f}%"
                    )
            else:
                check = ComplianceCheck(
                    check_name=check_name,
                    status=ComplianceCheck.CHECK_PASS,
                    severity=ComplianceCheck.SEVERITY_INFO,
                    message="No suspicious discounts detected"
                )
        
        self.checks_performed.append(check)
    
    @staticmethod
    def _safe_decimal(value) -> Decimal or None:
        """Safely convert value to Decimal."""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            try:
                return Decimal(value)
            except:
                return None
        try:
            return Decimal(str(value))
        except:
            return None


# Singleton instance
invoice_compliance_service = InvoiceComplianceService()
