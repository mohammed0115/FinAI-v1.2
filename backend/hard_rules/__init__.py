"""
Hard Rules Engine - محرك القواعد الصارمة

FINANCIAL SYSTEM GOVERNANCE VALIDATOR

This module provides deterministic, non-AI rule enforcement for all financial operations.
All rules MUST pass before any AI analysis or recommendation can proceed.

CRITICAL: These rules are DETERMINISTIC and NON-AI.
"""
from .engine import HardRulesEngine
from .validators import (
    AccountingRulesValidator,
    InvoiceRulesValidator,
    VATRulesValidator,
    ComplianceRulesValidator,
    OCRConfidenceValidator,
    SecurityAuditValidator,
)
from .gate import HardRulesGate, hard_rules_gate

__all__ = [
    'HardRulesEngine',
    'AccountingRulesValidator',
    'InvoiceRulesValidator',
    'VATRulesValidator',
    'ComplianceRulesValidator',
    'OCRConfidenceValidator',
    'SecurityAuditValidator',
    'HardRulesGate',
    'hard_rules_gate',
]
