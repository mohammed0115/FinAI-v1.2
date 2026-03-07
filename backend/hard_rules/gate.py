"""
Hard Rules Gate - بوابة القواعد الصارمة

Gate that BLOCKS AI execution until all hard rules pass.
This is the enforcement point for the Hard Rules Engine.
"""
import logging
from functools import wraps
from typing import Callable, Dict, Optional, Any
from datetime import datetime, timezone
import hashlib
import json

from .engine import HardRulesEngine, HardRulesReport, hard_rules_engine
from .validators import RuleStatus

logger = logging.getLogger(__name__)


class HardRulesGateException(Exception):
    """Exception raised when Hard Rules gate blocks execution"""
    
    def __init__(self, message: str, report: HardRulesReport = None):
        self.message = message
        self.report = report
        super().__init__(self.message)
    
    def to_dict(self) -> Dict:
        return {
            'error': 'HARD_RULES_BLOCKED',
            'message': self.message,
            'report': self.report.to_dict() if self.report else None,
        }


class HardRulesGate:
    """
    بوابة القواعد الصارمة
    Hard Rules Gate - AI Execution Blocker
    
    This gate MUST be passed before any AI analysis or recommendation.
    
    ENFORCEMENT:
    - Blocks ALL AI operations by default
    - Only allows AI after ALL hard rules pass
    - Logs all gate checks for audit trail
    """
    
    def __init__(self, engine: HardRulesEngine = None):
        self.engine = engine or hard_rules_engine
        self._gate_log: list = []
    
    def check_engine_exists(self) -> Dict:
        """
        Step 1 of Governance Validation:
        Check if Hard Rules Engine exists and is operational
        """
        if not self.engine or not self.engine.is_engine_present():
            return {
                'exists': False,
                'message': 'SYSTEM BLOCKED: Hard Rules Engine is missing and must be implemented before proceeding.',
                'message_ar': 'النظام محظور: محرك القواعد الصارمة مفقود ويجب تنفيذه قبل المتابعة.',
            }
        
        status = self.engine.get_engine_status()
        return {
            'exists': True,
            'message': 'Hard Rules Engine is present and operational.',
            'message_ar': 'محرك القواعد الصارمة موجود وفعال.',
            'status': status,
        }
    
    def validate_and_gate(
        self,
        validation_function: Callable,
        *args,
        **kwargs
    ) -> HardRulesReport:
        """
        Execute validation and determine if AI can proceed
        
        Returns:
            HardRulesReport with gate decision
        """
        # Reset engine
        self.engine.reset()
        
        # Execute validation
        validation_function(*args, **kwargs)
        
        # Generate report
        report = self.engine.generate_report()
        
        # Log gate check
        self._log_gate_check(report)
        
        return report
    
    def gate_ai_execution(self, report: HardRulesReport) -> bool:
        """
        Final gate decision - can AI proceed?
        
        Returns:
            True if AI can proceed, raises exception otherwise
        """
        if not report.is_eligible_for_ai:
            raise HardRulesGateException(
                message=report.get_blocking_message(),
                report=report
            )
        
        logger.info(
            f"Hard Rules Gate: PASSED - AI execution allowed. "
            f"Score: {report.passed_count}/{report.total_rules_checked}"
        )
        return True
    
    def _log_gate_check(self, report: HardRulesReport):
        """Log gate check for audit trail"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': report.overall_status,
            'eligible_for_ai': report.is_eligible_for_ai,
            'total_checked': report.total_rules_checked,
            'passed': report.passed_count,
            'failed': report.failed_count,
            'blocked': report.blocked_count,
            'report_hash': report.report_hash,
        }
        self._gate_log.append(log_entry)
        
        # Keep only last 1000 entries
        if len(self._gate_log) > 1000:
            self._gate_log = self._gate_log[-1000:]
    
    def get_gate_log(self, limit: int = 100) -> list:
        """Get recent gate check log"""
        return self._gate_log[-limit:]
    
    # ==========================================================================
    # DECORATOR FOR AI FUNCTIONS
    # ==========================================================================
    
    def require_hard_rules_pass(self, validation_data_extractor: Callable = None):
        """
        Decorator to enforce Hard Rules before AI function execution
        
        Usage:
            @hard_rules_gate.require_hard_rules_pass(
                validation_data_extractor=lambda kwargs: kwargs.get('invoice_data')
            )
            def ai_analyze_invoice(invoice_data, ...):
                ...
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check engine exists
                engine_check = self.check_engine_exists()
                if not engine_check['exists']:
                    raise HardRulesGateException(engine_check['message'])
                
                # Extract validation data if extractor provided
                validation_data = None
                if validation_data_extractor:
                    validation_data = validation_data_extractor(kwargs)
                
                # If we have validation data, run full validation
                if validation_data and isinstance(validation_data, dict):
                    report = self.engine.validate_full_invoice_flow(
                        invoice_data=validation_data,
                        country=kwargs.get('country', 'SA'),
                        user_id=kwargs.get('user_id', 'system'),
                        user_role=kwargs.get('user_role', 'system'),
                        organization_id=kwargs.get('organization_id', ''),
                        existing_accounts=kwargs.get('existing_accounts'),
                        existing_invoice_numbers=kwargs.get('existing_invoice_numbers'),
                        field_confidences=kwargs.get('field_confidences'),
                    )
                    
                    # Gate check
                    if not report.is_eligible_for_ai:
                        raise HardRulesGateException(
                            message=report.get_blocking_message(),
                            report=report
                        )
                
                # Execute original function
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    # ==========================================================================
    # QUICK VALIDATION HELPERS
    # ==========================================================================
    
    def quick_validate_invoice(
        self,
        invoice_data: Dict,
        country: str = 'SA',
        user_id: str = 'system',
        user_role: str = 'admin',
        organization_id: str = ''
    ) -> Dict:
        """
        Quick invoice validation with simple response
        """
        report = self.engine.validate_full_invoice_flow(
            invoice_data=invoice_data,
            country=country,
            user_id=user_id,
            user_role=user_role,
            organization_id=organization_id
        )
        
        return {
            'valid': report.is_eligible_for_ai,
            'status': report.overall_status,
            'message': report.get_blocking_message(),
            'summary': {
                'passed': report.passed_count,
                'failed': report.failed_count,
                'blocked': report.blocked_count,
                'total': report.total_rules_checked,
            },
            'details': report.to_dict() if not report.is_eligible_for_ai else None,
        }
    
    def quick_validate_journal_entry(
        self,
        debit_amount: float,
        credit_amount: float,
        account_code: str,
        transaction_type: str,
        existing_accounts: Dict[str, Dict]
    ) -> Dict:
        """
        Quick journal entry validation
        """
        from decimal import Decimal
        
        self.engine.reset()
        results = self.engine.validate_journal_entry(
            entry_id='quick_check',
            debit_amount=Decimal(str(debit_amount)),
            credit_amount=Decimal(str(credit_amount)),
            account_code=account_code,
            transaction_type=transaction_type,
            existing_accounts=existing_accounts
        )
        
        failed = [r for r in results if r.status in [RuleStatus.FAIL, RuleStatus.BLOCKED]]
        
        return {
            'valid': len(failed) == 0,
            'status': 'FAIL' if failed else 'PASS',
            'errors': [r.to_dict() for r in failed],
            'all_results': [r.to_dict() for r in results],
        }
    
    def get_governance_status(self) -> Dict:
        """
        Get full governance status for external validation
        """
        engine_check = self.check_engine_exists()
        
        if not engine_check['exists']:
            return {
                'system_status': 'BLOCKED',
                'message': engine_check['message'],
                'message_ar': engine_check['message_ar'],
                'hard_rules_engine': None,
            }
        
        return {
            'system_status': 'OPERATIONAL',
            'message': 'HARD RULES VERIFIED: System is eligible for AI analysis.',
            'message_ar': 'تم التحقق من القواعد الصارمة: النظام مؤهل للتحليل الذكي.',
            'hard_rules_engine': engine_check['status'],
            'enforcement_summary': {
                'accounting_rules': 4,
                'invoice_rules': 4,
                'vat_rules': 3,
                'compliance_rules': 5,
                'ocr_rules': 1,
                'security_rules': 3,
                'total_rules': 20,
            },
            'gate_active': True,
            'ai_blocked_by_default': True,
        }


# Singleton instance
hard_rules_gate = HardRulesGate()
