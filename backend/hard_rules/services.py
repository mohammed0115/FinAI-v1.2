"""
Hard Rules Service - خدمة القواعد الصارمة

Django service that integrates Hard Rules Engine with the application.
Provides logging, database persistence, and API integration.
"""
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime

from django.utils import timezone
from django.db import transaction

from .engine import HardRulesEngine, HardRulesReport, hard_rules_engine
from .gate import HardRulesGate, HardRulesGateException, hard_rules_gate
from .models import HardRulesEvaluation, HardRulesRuleResult, AIExecutionGateLog

logger = logging.getLogger(__name__)


class HardRulesService:
    """
    خدمة القواعد الصارمة
    Hard Rules Service for Django Integration
    """
    
    def __init__(self):
        self.engine = hard_rules_engine
        self.gate = hard_rules_gate
    
    def validate_invoice_with_logging(
        self,
        invoice_data: Dict,
        country: str,
        user_id: str,
        user_role: str,
        organization_id: str,
        existing_accounts: Dict[str, Dict] = None,
        existing_invoice_numbers: set = None,
        field_confidences: Dict[str, int] = None,
        save_to_db: bool = True
    ) -> Dict:
        """
        Validate invoice and log results to database
        """
        # Run validation
        report = self.engine.validate_full_invoice_flow(
            invoice_data=invoice_data,
            country=country,
            user_id=user_id,
            user_role=user_role,
            organization_id=organization_id,
            existing_accounts=existing_accounts,
            existing_invoice_numbers=existing_invoice_numbers,
            field_confidences=field_confidences,
        )
        
        # Save to database
        evaluation = None
        if save_to_db:
            evaluation = self._save_evaluation(
                report=report,
                evaluation_type='invoice',
                entity_type='invoice',
                entity_id=str(invoice_data.get('id', invoice_data.get('uuid', ''))),
                organization_id=organization_id,
                user_id=user_id
            )
        
        return {
            'valid': report.is_eligible_for_ai,
            'status': report.overall_status,
            'message': report.get_blocking_message(),
            'report': report.to_dict(),
            'evaluation_id': str(evaluation.id) if evaluation else None,
        }
    
    def validate_journal_entry_with_logging(
        self,
        entry_id: str,
        debit_amount: Decimal,
        credit_amount: Decimal,
        account_code: str,
        transaction_type: str,
        existing_accounts: Dict[str, Dict],
        organization_id: str = None,
        user_id: str = None,
        save_to_db: bool = True
    ) -> Dict:
        """
        Validate journal entry and log results
        """
        self.engine.reset()
        
        # Run validation
        results = self.engine.validate_journal_entry(
            entry_id=entry_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            account_code=account_code,
            transaction_type=transaction_type,
            existing_accounts=existing_accounts
        )
        
        # Generate report
        report = self.engine.generate_report()
        
        # Save to database
        evaluation = None
        if save_to_db:
            evaluation = self._save_evaluation(
                report=report,
                evaluation_type='journal_entry',
                entity_type='journal_entry',
                entity_id=entry_id,
                organization_id=organization_id,
                user_id=user_id
            )
        
        return {
            'valid': report.is_eligible_for_ai,
            'status': report.overall_status,
            'message': report.get_blocking_message(),
            'results': [r.to_dict() for r in results],
            'evaluation_id': str(evaluation.id) if evaluation else None,
        }
    
    def check_ai_gate(
        self,
        ai_function_name: str,
        invoice_data: Dict = None,
        organization_id: str = None,
        user_id: str = None,
        country: str = 'SA'
    ) -> Dict:
        """
        Check if AI execution is allowed
        """
        # Check engine exists
        engine_check = self.gate.check_engine_exists()
        if not engine_check['exists']:
            self._log_ai_gate_decision(
                decision='BLOCKED',
                ai_function_name=ai_function_name,
                organization_id=organization_id,
                user_id=user_id,
                blocking_reason=engine_check['message']
            )
            return {
                'allowed': False,
                'reason': engine_check['message'],
                'reason_ar': engine_check['message_ar'],
            }
        
        # If invoice data provided, validate it
        if invoice_data:
            result = self.validate_invoice_with_logging(
                invoice_data=invoice_data,
                country=country,
                user_id=user_id or 'system',
                user_role='system',
                organization_id=organization_id or '',
                save_to_db=True
            )
            
            if not result['valid']:
                self._log_ai_gate_decision(
                    decision='BLOCKED',
                    ai_function_name=ai_function_name,
                    organization_id=organization_id,
                    user_id=user_id,
                    blocking_reason=result['message']
                )
                return {
                    'allowed': False,
                    'reason': result['message'],
                    'validation_report': result['report'],
                }
        
        # AI allowed
        self._log_ai_gate_decision(
            decision='ALLOWED',
            ai_function_name=ai_function_name,
            organization_id=organization_id,
            user_id=user_id
        )
        
        return {
            'allowed': True,
            'message': 'HARD RULES VERIFIED: AI execution allowed.',
            'message_ar': 'تم التحقق من القواعد الصارمة: تنفيذ الذكاء الاصطناعي مسموح.',
        }
    
    def get_governance_status(self) -> Dict:
        """
        Get governance status for dashboard
        """
        return self.gate.get_governance_status()
    
    def get_rule_enforcement_summary(self) -> Dict:
        """
        Get summary of rule enforcement
        """
        engine_status = self.engine.get_engine_status()
        
        return {
            'engine_operational': True,
            'rules': engine_status['rules_enforced'],
            'categories': {
                'accounting': {
                    'rules': ['ACC-001', 'ACC-002', 'ACC-003', 'ACC-004'],
                    'description': 'Debit/Credit balance, zero-value, account validation',
                    'description_ar': 'توازن المدين/الدائن، القيم الصفرية، التحقق من الحسابات',
                },
                'invoice': {
                    'rules': ['INV-001', 'INV-002', 'INV-003', 'INV-004'],
                    'description': 'Mandatory fields, total calculation, date, currency',
                    'description_ar': 'الحقول الإلزامية، حساب المجموع، التاريخ، العملة',
                },
                'vat': {
                    'rules': ['VAT-001', 'VAT-002', 'VAT-003'],
                    'description': 'Rate validation, calculation, exemption justification',
                    'description_ar': 'التحقق من النسبة، الحساب، مبرر الإعفاء',
                },
                'compliance': {
                    'rules': ['CMP-001', 'CMP-002', 'CMP-003', 'CMP-004', 'CMP-005'],
                    'description': 'UUID, QR code, schema, uniqueness, invoice type',
                    'description_ar': 'المعرف الفريد، رمز QR، المخطط، التفرد، نوع الفاتورة',
                },
                'ocr': {
                    'rules': ['OCR-001'],
                    'description': 'Critical field confidence threshold',
                    'description_ar': 'حد ثقة الحقول الحرجة',
                },
                'security': {
                    'rules': ['SEC-001', 'SEC-002', 'SEC-003'],
                    'description': 'Permissions, segregation of duties, audit trail',
                    'description_ar': 'الصلاحيات، فصل المهام، سجل التدقيق',
                },
            },
            'enforcement_type': 'DETERMINISTIC',
            'ai_blocked_by_default': True,
        }
    
    def get_recent_evaluations(
        self,
        organization_id: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get recent Hard Rules evaluations
        """
        queryset = HardRulesEvaluation.objects.all()
        
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        
        evaluations = queryset[:limit]
        
        return [
            {
                'id': str(e.id),
                'type': e.evaluation_type,
                'status': e.overall_status,
                'eligible_for_ai': e.is_eligible_for_ai,
                'summary': {
                    'total': e.total_rules_checked,
                    'passed': e.passed_count,
                    'failed': e.failed_count,
                    'blocked': e.blocked_count,
                },
                'evaluated_at': e.evaluated_at.isoformat(),
            }
            for e in evaluations
        ]
    
    def _save_evaluation(
        self,
        report: HardRulesReport,
        evaluation_type: str,
        entity_type: str,
        entity_id: str,
        organization_id: str = None,
        user_id: str = None
    ) -> HardRulesEvaluation:
        """
        Save evaluation to database
        """
        # Validate UUIDs - only use if valid
        valid_org_id = None
        valid_user_id = None
        
        if organization_id:
            try:
                import uuid
                uuid.UUID(organization_id)
                valid_org_id = organization_id
            except (ValueError, TypeError):
                pass
        
        if user_id:
            try:
                import uuid
                uuid.UUID(user_id)
                valid_user_id = user_id
            except (ValueError, TypeError):
                pass
        
        with transaction.atomic():
            # Create main evaluation record
            evaluation = HardRulesEvaluation.objects.create(
                organization_id=valid_org_id,
                user_id=valid_user_id,
                evaluation_type=evaluation_type,
                entity_type=entity_type,
                entity_id=entity_id,
                overall_status=report.overall_status,
                is_eligible_for_ai=report.is_eligible_for_ai,
                total_rules_checked=report.total_rules_checked,
                passed_count=report.passed_count,
                failed_count=report.failed_count,
                blocked_count=report.blocked_count,
                warning_count=report.warning_count,
                results_json=report.results_by_category,
                critical_failures_json=report.critical_failures,
                blocking_issues_json=report.blocking_issues,
                blocking_message=report.get_blocking_message(),
                report_hash=report.report_hash,
            )
            
            # Create individual rule results
            for category, results in report.results_by_category.items():
                for result in results:
                    HardRulesRuleResult.objects.create(
                        evaluation=evaluation,
                        rule_id=result['rule_id'],
                        rule_name=result['rule_name'],
                        rule_name_ar=result['rule_name_ar'],
                        category=category,
                        status=result['status'],
                        message=result['message'],
                        message_ar=result['message_ar'],
                        details_json=result.get('details'),
                    )
            
            return evaluation
    
    def _log_ai_gate_decision(
        self,
        decision: str,
        ai_function_name: str,
        organization_id: str = None,
        user_id: str = None,
        blocking_reason: str = None,
        evaluation: HardRulesEvaluation = None
    ):
        """
        Log AI gate decision
        """
        # Validate UUIDs
        valid_org_id = None
        valid_user_id = None
        
        if organization_id:
            try:
                import uuid
                uuid.UUID(organization_id)
                valid_org_id = organization_id
            except (ValueError, TypeError):
                pass
        
        if user_id:
            try:
                import uuid
                uuid.UUID(user_id)
                valid_user_id = user_id
            except (ValueError, TypeError):
                pass
        
        AIExecutionGateLog.objects.create(
            organization_id=valid_org_id,
            user_id=valid_user_id,
            decision=decision,
            ai_function_name=ai_function_name,
            evaluation=evaluation,
            blocking_reason=blocking_reason,
        )


# Singleton instance
hard_rules_service = HardRulesService()
