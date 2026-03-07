# Invoice Risk Scoring Service
# Computes numeric risk score (0-100) based on compliance checks
# Derives risk level (Low, Medium, High, Critical)

import logging
from typing import Tuple
from .invoice_compliance_service import ComplianceCheck

logger = logging.getLogger(__name__)


class InvoiceRiskScoringService:
    """Compute risk score and level based on compliance checks."""
    
    RISK_LEVEL_LOW = "Low"
    RISK_LEVEL_MEDIUM = "Medium"
    RISK_LEVEL_HIGH = "High"
    RISK_LEVEL_CRITICAL = "Critical"
    
    # Risk weight for each severity level
    SEVERITY_WEIGHTS = {
        ComplianceCheck.SEVERITY_INFO: 0,      # No risk
        ComplianceCheck.SEVERITY_WARNING: 10,   # Minor risk
        ComplianceCheck.SEVERITY_ERROR: 25,     # Moderate risk
        ComplianceCheck.SEVERITY_CRITICAL: 50,  # Severe risk
    }
    
    # Risk weight for check status
    STATUS_WEIGHTS = {
        ComplianceCheck.CHECK_PASS: 0,        # No risk
        ComplianceCheck.CHECK_AVAILABLE: 5,   # Data present but incomplete
        ComplianceCheck.CHECK_WARNING: 15,    # Warning level issue
        ComplianceCheck.CHECK_INVALID: 25,    # Invalid data
        ComplianceCheck.CHECK_MISSING: 40,    # Missing critical data
    }
    
    def __init__(self):
        self.checks = []
        self.risk_score = 0
        self.risk_level = self.RISK_LEVEL_LOW
    
    def compute_risk_score(self, compliance_checks: list) -> Tuple[int, str]:
        """
        Compute overall risk score (0-100) and risk level.
        
        Returns: (risk_score: int, risk_level: str)
        """
        self.checks = compliance_checks
        self.risk_score = 0
        
        if not compliance_checks:
            self.risk_level = self.RISK_LEVEL_LOW
            return 0, self.RISK_LEVEL_LOW
        
        # Calculate aggregate risk
        total_weight = 0
        critical_count = 0
        error_count = 0
        warning_count = 0
        
        for check in compliance_checks:
            # Weight by severity (primary)
            severity_weight = self.SEVERITY_WEIGHTS.get(check.severity, 0)
            
            # Weight by status (secondary)
            status_weight = self.STATUS_WEIGHTS.get(check.status, 0)
            
            # Combined weight
            combined_weight = severity_weight + status_weight
            total_weight += combined_weight
            
            # Count issues by severity
            if check.severity == ComplianceCheck.SEVERITY_CRITICAL:
                critical_count += 1
            elif check.severity == ComplianceCheck.SEVERITY_ERROR:
                error_count += 1
            elif check.severity == ComplianceCheck.SEVERITY_WARNING:
                warning_count += 1
        
        # Normalize risk score (0-100)
        # Each check can contribute up to 50 points
        # With 9 checks max, theoretical max = 450
        # Cap at 100
        self.risk_score = min(100, int(total_weight))
        
        # Determine risk level based on score and critical issues
        if critical_count > 0:
            self.risk_level = self.RISK_LEVEL_CRITICAL
        elif self.risk_score >= 80 or error_count >= 3:
            self.risk_level = self.RISK_LEVEL_HIGH
        elif self.risk_score >= 40 or error_count >= 1:
            self.risk_level = self.RISK_LEVEL_MEDIUM
        else:
            self.risk_level = self.RISK_LEVEL_LOW
        
        logger.info(
            f"Risk computed: score={self.risk_score}, level={self.risk_level}, "
            f"critical={critical_count}, error={error_count}, warning={warning_count}"
        )
        
        return self.risk_score, self.risk_level
    
    def get_risk_summary(self) -> dict:
        """Get detailed risk summary."""
        if not self.checks:
            return {
                "risk_score": 0,
                "risk_level": self.RISK_LEVEL_LOW,
                "critical_checks": [],
                "error_checks": [],
                "warning_checks": [],
                "total_checks": 0
            }
        
        critical_checks = [c for c in self.checks if c.severity == ComplianceCheck.SEVERITY_CRITICAL]
        error_checks = [c for c in self.checks if c.severity == ComplianceCheck.SEVERITY_ERROR]
        warning_checks = [c for c in self.checks if c.severity == ComplianceCheck.SEVERITY_WARNING]
        
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "critical_checks": [c.to_dict() for c in critical_checks],
            "error_checks": [c.to_dict() for c in error_checks],
            "warning_checks": [c.to_dict() for c in warning_checks],
            "total_checks": len(self.checks),
            "summary": self._generate_summary(critical_checks, error_checks, warning_checks)
        }
    
    def _generate_summary(self, critical: list, errors: list, warnings: list) -> str:
        """Generate human-readable risk summary."""
        if not critical and not errors and not warnings:
            return "All compliance checks passed. Low risk invoice."
        
        parts = []
        
        if critical:
            parts.append(f"{len(critical)} critical issue(s) found")
        
        if errors:
            parts.append(f"{len(errors)} error(s) found")
        
        if warnings:
            parts.append(f"{len(warnings)} warning(s) found")
        
        summary = ", ".join(parts) + "."
        
        # Add risk level context
        if self.risk_level == self.RISK_LEVEL_CRITICAL:
            summary += " CRITICAL RISK - Requires immediate review."
        elif self.risk_level == self.RISK_LEVEL_HIGH:
            summary += " HIGH RISK - Review before posting."
        elif self.risk_level == self.RISK_LEVEL_MEDIUM:
            summary += " MEDIUM RISK - Recommend review."
        
        return summary


# Singleton instance
invoice_risk_scoring_service = InvoiceRiskScoringService()
