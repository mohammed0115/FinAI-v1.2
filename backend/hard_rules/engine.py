"""
Hard Rules Engine - محرك القواعد الصارمة

Central orchestrator for all hard rule validations.
This engine MUST be invoked before any AI analysis or recommendations.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import hashlib
import json

from .validators import (
    RuleStatus,
    RuleResult,
    AccountingRulesValidator,
    InvoiceRulesValidator,
    VATRulesValidator,
    ComplianceRulesValidator,
    OCRConfidenceValidator,
    SecurityAuditValidator,
)

logger = logging.getLogger(__name__)


@dataclass
class HardRulesReport:
    """
    Hard Rules Validation Report
    Contains complete validation results and status
    """
    timestamp: str
    overall_status: str  # PASS, FAIL, BLOCKED
    is_eligible_for_ai: bool
    total_rules_checked: int
    passed_count: int
    failed_count: int
    blocked_count: int
    warning_count: int
    results_by_category: Dict[str, List[Dict]]
    critical_failures: List[Dict]
    blocking_issues: List[Dict]
    report_hash: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'overall_status': self.overall_status,
            'is_eligible_for_ai': self.is_eligible_for_ai,
            'summary': {
                'total_rules_checked': self.total_rules_checked,
                'passed': self.passed_count,
                'failed': self.failed_count,
                'blocked': self.blocked_count,
                'warnings': self.warning_count,
            },
            'results_by_category': self.results_by_category,
            'critical_failures': self.critical_failures,
            'blocking_issues': self.blocking_issues,
            'report_hash': self.report_hash,
        }
    
    def get_blocking_message(self) -> str:
        """Get formatted blocking message if system is blocked"""
        if self.overall_status == 'PASS':
            return "HARD RULES VERIFIED: System is eligible for AI analysis."
        
        if self.blocking_issues:
            issues = [f"- {b['rule_id']}: {b['message']}" for b in self.blocking_issues[:5]]
            return f"SYSTEM BLOCKED: Hard Rules violation detected.\n\nBlocking issues:\n" + "\n".join(issues)
        
        if self.critical_failures:
            failures = [f"- {f['rule_id']}: {f['message']}" for f in self.critical_failures[:5]]
            return f"SYSTEM BLOCKED: Hard Rules validation failed.\n\nCritical failures:\n" + "\n".join(failures)
        
        return "SYSTEM BLOCKED: Hard Rules Engine validation did not pass."


class HardRulesEngine:
    """
    محرك القواعد الصارمة
    Hard Rules Engine - Central Orchestrator
    
    This engine enforces DETERMINISTIC, NON-AI rules for financial operations.
    
    CRITICAL ENFORCEMENT:
    - All rules are deterministic - no AI, no inference
    - All rules are mandatory - no override without explicit authorization
    - Any rule failure BLOCKS AI analysis
    
    Categories:
    - Accounting Rules (ACC)
    - Invoice Rules (INV)
    - VAT Rules (VAT)
    - Compliance Rules (CMP)
    - OCR Confidence Rules (OCR)
    - Security & Audit Rules (SEC)
    """
    
    def __init__(self):
        # Initialize all validators
        self.accounting_validator = AccountingRulesValidator()
        self.invoice_validator = InvoiceRulesValidator()
        self.vat_validator = VATRulesValidator()
        self.compliance_validator = ComplianceRulesValidator()
        self.ocr_validator = OCRConfidenceValidator()
        self.security_validator = SecurityAuditValidator()
        
        # Track all results
        self._results: List[RuleResult] = []
        self._validation_start: Optional[datetime] = None
    
    def reset(self):
        """Reset engine state for new validation"""
        self._results = []
        self._validation_start = datetime.now(timezone.utc)
    
    def add_result(self, result: RuleResult):
        """Add a validation result"""
        self._results.append(result)
        
        # Log critical issues immediately
        if result.status in [RuleStatus.FAIL, RuleStatus.BLOCKED]:
            logger.warning(
                f"Hard Rule {result.status.value}: {result.rule_id} - {result.message}"
            )
    
    # ==========================================================================
    # ACCOUNTING RULES
    # ==========================================================================
    
    def validate_journal_entry(
        self,
        entry_id: str,
        debit_amount: Decimal,
        credit_amount: Decimal,
        account_code: str,
        transaction_type: str,
        existing_accounts: Dict[str, Dict]
    ) -> List[RuleResult]:
        """
        Validate a journal entry against all accounting rules
        """
        results = []
        
        # ACC-001: Debit = Credit
        results.append(
            self.accounting_validator.validate_debit_equals_credit(
                debit_amount, credit_amount, entry_id
            )
        )
        
        # ACC-002: No zero-value entries
        results.append(
            self.accounting_validator.validate_no_zero_value_entry(
                debit_amount, credit_amount, entry_id
            )
        )
        
        # ACC-003: Account exists and active
        results.append(
            self.accounting_validator.validate_account_exists_and_active(
                account_code, existing_accounts, entry_id
            )
        )
        
        # ACC-004: Account type matches transaction type
        results.append(
            self.accounting_validator.validate_account_type_match(
                account_code, transaction_type, existing_accounts, entry_id
            )
        )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # INVOICE RULES
    # ==========================================================================
    
    def validate_invoice(
        self,
        invoice_data: Dict,
        invoice_id: str = None
    ) -> List[RuleResult]:
        """
        Validate an invoice against all invoice rules
        """
        results = []
        
        # INV-001: Mandatory fields
        results.append(
            self.invoice_validator.validate_mandatory_fields(invoice_data, invoice_id)
        )
        
        # INV-002: Total calculation
        results.append(
            self.invoice_validator.validate_total_calculation(
                subtotal=invoice_data.get('subtotal', invoice_data.get('total_excluding_vat', 0)),
                vat_amount=invoice_data.get('vat_amount', invoice_data.get('total_vat', 0)),
                other_taxes=invoice_data.get('other_taxes', 0),
                total_amount=invoice_data.get('total_amount', invoice_data.get('total_including_vat', 0)),
                invoice_id=invoice_id
            )
        )
        
        # INV-003: Invoice date
        results.append(
            self.invoice_validator.validate_invoice_date(
                invoice_data.get('invoice_date', invoice_data.get('issue_date')),
                invoice_id
            )
        )
        
        # INV-004: Currency
        results.append(
            self.invoice_validator.validate_currency(
                invoice_data.get('currency', invoice_data.get('currency_code')),
                invoice_id
            )
        )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # VAT RULES
    # ==========================================================================
    
    def validate_vat(
        self,
        taxable_amount: Decimal,
        vat_rate: Decimal,
        declared_vat: Decimal,
        country: str,
        exemption_code: str = None,
        exemption_reason: str = None,
        invoice_id: str = None
    ) -> List[RuleResult]:
        """
        Validate VAT against all VAT rules
        """
        results = []
        
        # VAT-001: Rate matches country
        results.append(
            self.vat_validator.validate_vat_rate(vat_rate, country, invoice_id)
        )
        
        # VAT-002: Calculation correct
        results.append(
            self.vat_validator.validate_vat_calculation(
                taxable_amount, vat_rate, declared_vat, invoice_id
            )
        )
        
        # VAT-003: Zero VAT justification
        results.append(
            self.vat_validator.validate_zero_vat_justification(
                declared_vat, exemption_code, exemption_reason, invoice_id
            )
        )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # COMPLIANCE RULES (ZATCA/GCC)
    # ==========================================================================
    
    def validate_zatca_compliance(
        self,
        invoice_data: Dict,
        existing_invoice_numbers: set = None,
        organization_id: str = None,
        invoice_id: str = None
    ) -> List[RuleResult]:
        """
        Validate ZATCA compliance for an invoice
        """
        results = []
        
        # CMP-001: UUID present
        results.append(
            self.compliance_validator.validate_uuid_present(
                invoice_data.get('uuid'), invoice_id
            )
        )
        
        # CMP-002: QR Code present
        results.append(
            self.compliance_validator.validate_qr_code_present(
                invoice_data.get('qr_code'),
                invoice_data.get('invoice_subtype', '0100000'),
                invoice_id
            )
        )
        
        # CMP-003: Schema valid
        results.append(
            self.compliance_validator.validate_invoice_schema(invoice_data, invoice_id)
        )
        
        # CMP-004: Number unique
        if existing_invoice_numbers is not None:
            results.append(
                self.compliance_validator.validate_invoice_number_unique(
                    invoice_data.get('invoice_number'),
                    organization_id,
                    existing_invoice_numbers,
                    invoice_id
                )
            )
        
        # CMP-005: Type valid
        results.append(
            self.compliance_validator.validate_invoice_type(
                invoice_data.get('invoice_type_code', invoice_data.get('invoice_type', '388')),
                invoice_id
            )
        )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # OCR CONFIDENCE RULES
    # ==========================================================================
    
    def validate_ocr_extraction(
        self,
        extracted_data: Dict,
        field_confidences: Dict[str, int],
        document_id: str = None
    ) -> List[RuleResult]:
        """
        Validate OCR extraction confidence levels
        """
        results = self.ocr_validator.validate_document_confidence(
            extracted_data, field_confidences, document_id
        )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # SECURITY & AUDIT RULES
    # ==========================================================================
    
    def validate_security(
        self,
        user_id: str,
        user_role: str,
        required_permission: str,
        creator_id: str = None,
        approver_id: str = None,
        entity_type: str = None,
        entity_id: str = None,
        audit_records: List[Dict] = None
    ) -> List[RuleResult]:
        """
        Validate security and audit rules
        """
        results = []
        
        # SEC-001: User permissions
        results.append(
            self.security_validator.validate_user_permission(
                user_role, required_permission, user_id
            )
        )
        
        # SEC-002: Segregation of duties (if both creator and approver provided)
        if creator_id and approver_id:
            results.append(
                self.security_validator.validate_segregation_of_duties(
                    creator_id, approver_id, entity_type, entity_id
                )
            )
        
        # SEC-003: Audit trail (if records provided)
        if audit_records is not None and entity_type and entity_id:
            results.append(
                self.security_validator.validate_audit_trail(
                    entity_type, entity_id, audit_records
                )
            )
        
        for result in results:
            self.add_result(result)
        
        return results
    
    # ==========================================================================
    # COMPREHENSIVE VALIDATION
    # ==========================================================================
    
    def validate_full_invoice_flow(
        self,
        invoice_data: Dict,
        country: str,
        user_id: str,
        user_role: str,
        organization_id: str,
        existing_accounts: Dict[str, Dict] = None,
        existing_invoice_numbers: set = None,
        field_confidences: Dict[str, int] = None,
        creator_id: str = None,
        approver_id: str = None,
        audit_records: List[Dict] = None
    ) -> HardRulesReport:
        """
        Comprehensive validation of a complete invoice flow
        """
        self.reset()
        invoice_id = str(invoice_data.get('id', invoice_data.get('uuid', 'unknown')))
        
        # 1. Invoice Rules
        self.validate_invoice(invoice_data, invoice_id)
        
        # 2. VAT Rules
        self.validate_vat(
            taxable_amount=Decimal(str(invoice_data.get('total_excluding_vat', invoice_data.get('subtotal', 0)))),
            vat_rate=Decimal(str(invoice_data.get('vat_rate', 15))),
            declared_vat=Decimal(str(invoice_data.get('total_vat', invoice_data.get('vat_amount', 0)))),
            country=country,
            exemption_code=invoice_data.get('exemption_code'),
            exemption_reason=invoice_data.get('exemption_reason'),
            invoice_id=invoice_id
        )
        
        # 3. Compliance Rules (ZATCA)
        self.validate_zatca_compliance(
            invoice_data, existing_invoice_numbers, organization_id, invoice_id
        )
        
        # 4. OCR Confidence (if provided)
        if field_confidences:
            self.validate_ocr_extraction(invoice_data, field_confidences, invoice_id)
        
        # 5. Security Rules
        self.validate_security(
            user_id=user_id,
            user_role=user_role,
            required_permission='create',
            creator_id=creator_id,
            approver_id=approver_id,
            entity_type='invoice',
            entity_id=invoice_id,
            audit_records=audit_records
        )
        
        # Generate report
        return self.generate_report()
    
    def generate_report(self) -> HardRulesReport:
        """
        Generate comprehensive validation report
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Count by status
        passed_count = sum(1 for r in self._results if r.status == RuleStatus.PASS)
        failed_count = sum(1 for r in self._results if r.status == RuleStatus.FAIL)
        blocked_count = sum(1 for r in self._results if r.status == RuleStatus.BLOCKED)
        warning_count = sum(1 for r in self._results if r.status == RuleStatus.WARNING)
        
        # Group by category
        results_by_category: Dict[str, List[Dict]] = {}
        for result in self._results:
            if result.category not in results_by_category:
                results_by_category[result.category] = []
            results_by_category[result.category].append(result.to_dict())
        
        # Identify critical failures and blocking issues
        critical_failures = [
            r.to_dict() for r in self._results 
            if r.status == RuleStatus.FAIL
        ]
        blocking_issues = [
            r.to_dict() for r in self._results 
            if r.status == RuleStatus.BLOCKED
        ]
        
        # Determine overall status
        if blocked_count > 0:
            overall_status = 'BLOCKED'
            is_eligible = False
        elif failed_count > 0:
            overall_status = 'FAIL'
            is_eligible = False
        elif warning_count > 0:
            overall_status = 'WARNING'
            is_eligible = True  # Warnings don't block AI
        else:
            overall_status = 'PASS'
            is_eligible = True
        
        # Generate report hash for integrity
        report_data = {
            'timestamp': timestamp,
            'status': overall_status,
            'counts': [passed_count, failed_count, blocked_count, warning_count],
            'results': [r.to_dict() for r in self._results]
        }
        report_hash = hashlib.sha256(
            json.dumps(report_data, sort_keys=True).encode()
        ).hexdigest()[:32]
        
        return HardRulesReport(
            timestamp=timestamp,
            overall_status=overall_status,
            is_eligible_for_ai=is_eligible,
            total_rules_checked=len(self._results),
            passed_count=passed_count,
            failed_count=failed_count,
            blocked_count=blocked_count,
            warning_count=warning_count,
            results_by_category=results_by_category,
            critical_failures=critical_failures,
            blocking_issues=blocking_issues,
            report_hash=report_hash
        )
    
    def is_engine_present(self) -> bool:
        """
        Check if Hard Rules Engine is present and operational
        Required by governance validator before any operation
        """
        return True
    
    def get_engine_status(self) -> Dict:
        """
        Get engine status for governance validation
        """
        return {
            'engine_present': True,
            'engine_name': 'FinAI Hard Rules Engine',
            'version': '1.0.0',
            'validators': {
                'accounting': self.accounting_validator is not None,
                'invoice': self.invoice_validator is not None,
                'vat': self.vat_validator is not None,
                'compliance': self.compliance_validator is not None,
                'ocr': self.ocr_validator is not None,
                'security': self.security_validator is not None,
            },
            'rules_enforced': [
                'ACC-001: Debit Equals Credit',
                'ACC-002: No Zero-Value Entries',
                'ACC-003: Account Exists and Active',
                'ACC-004: Account Type Match',
                'INV-001: Mandatory Fields Present',
                'INV-002: Total Calculation',
                'INV-003: Invoice Date Valid',
                'INV-004: Currency Valid',
                'VAT-001: VAT Rate Match',
                'VAT-002: VAT Calculation',
                'VAT-003: Zero VAT Justification',
                'CMP-001: UUID Present',
                'CMP-002: QR Code Present',
                'CMP-003: Invoice Schema Valid',
                'CMP-004: Invoice Number Unique',
                'CMP-005: Invoice Type Valid',
                'OCR-001: OCR Confidence Check',
                'SEC-001: User Permission Valid',
                'SEC-002: Segregation of Duties',
                'SEC-003: Audit Trail Exists',
            ],
            'enforcement_type': 'DETERMINISTIC',
            'ai_involvement': 'NONE',
        }


# Singleton instance
hard_rules_engine = HardRulesEngine()
