"""
ZATCA Compliance AI Module

Provides AI-powered analysis of ZATCA (Zakat, Tax and Customs Authority)
compliance results, violation detection, and remediation recommendations.

Features:
- Compliance result interpretation
- Violation detection and categorization
- Risk assessment
- Remediation recommendations
- Invoice structure validation
- Bilingual support (Arabic/English)
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.ai.client import get_openai_client
from core.ai.errors import AIAPIError

logger = logging.getLogger(__name__)


class ZATCAComplianceAI:
    """
    Analyzes and interprets ZATCA compliance results, detects violations,
    and provides remediation guidance.
    """

    def __init__(self):
        self.client = get_openai_client()
        self.model = 'gpt-4o-mini'

    def analyze_zatca_result(
        self,
        invoice_number: str,
        zatca_validation_message: str,
        zatca_status_code: Optional[str] = None,
        validation_status: str = 'pending',
        error_details: Optional[str] = None,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Analyze ZATCA validation result and provide interpretation.

        Args:
            invoice_number: Invoice identifier
            zatca_validation_message: ZATCA validation message
            zatca_status_code: ZATCA status code (e.g., 1001, 1002)
            validation_status: 'passed', 'failed', 'warning', 'pending'
            error_details: Additional error information
            language: Response language ('ar' or 'en')

        Returns:
            Dict with:
            - invoice_number: Invoice identifier
            - compliance_status: pass|warning|fail
            - compliance_score: 0-100 score
            - validation_message: User-friendly message
            - issues_found: List of compliance issues
            - violation_severity: critical|high|medium|low
            - remediation_steps: Steps to fix issues
            - zatca_requirements: Relevant ZATCA requirements
            - next_steps: Recommended actions
            - resubmission_required: Whether resubmission is needed
            - timestamp: Processing timestamp
        """
        try:
            start_time = datetime.utcnow()

            # Parse ZATCA result
            result_interpretation = self._interpret_zatca_result(
                zatca_validation_message, zatca_status_code, validation_status
            )

            # Identify specific violations
            violations = self._identify_violations(
                result_interpretation, error_details, language
            )

            # Assess compliance risk
            risk_assessment = self._assess_compliance_risk(
                violations, validation_status, language
            )

            # Generate remediation plan
            remediation = self._generate_remediation_plan(
                violations, language
            )

            # Determine resubmission requirements
            resubmission_needed = self._check_resubmission_required(
                violations, risk_assessment
            )

            result = {
                'invoice_number': invoice_number,
                'zatca_status_code': zatca_status_code,
                'original_status': validation_status,
                'compliance_status': result_interpretation['status'],
                'compliance_score': result_interpretation['score'],
                'user_friendly_message': result_interpretation['user_message'],
                'technical_message': zatca_validation_message[:200],
                'issues_found': violations['issues'],
                'issue_count': len(violations['issues']),
                'violation_categories': violations['categories'],
                'violation_severity': self._assess_severity_level(violations),
                'critical_issues': violations.get('critical', []),
                'remediation_steps': remediation['steps'],
                'remediation_priority': remediation['priority'],
                'estimated_remediation_time_hours': remediation['estimated_hours'],
                'zatca_article_references': remediation['article_references'],
                'compliance_requirements': self._map_zatca_requirements(violations),
                'next_actions': self._generate_next_actions(
                    result_interpretation, violations, resubmission_needed, language
                ),
                'resubmission_required': resubmission_needed,
                'resubmission_deadline': self._calculate_resubmission_deadline(violations),
                'similar_issues_history': self._get_similar_issues_history(violations),
                'audit_trail': {
                    'analysis_timestamp': start_time.isoformat(),
                    'analyzer_version': '1.0',
                    'confidence': result_interpretation['confidence']
                },
                'language': language,
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }

            logger.info(f"ZATCA compliance analysis completed: {invoice_number} ({result_interpretation['status']})")
            return result

        except Exception as e:
            logger.error(f"ZATCA compliance analysis error: {str(e)}", exc_info=True)
            raise AIAPIError(f"ZATCA analysis failed: {str(e)}")

    def _interpret_zatca_result(
        self,
        zatca_message: str,
        status_code: Optional[str],
        status: str
    ) -> Dict[str, Any]:
        """Interpret ZATCA validation result."""
        # Map ZATCA status codes
        zatca_codes = {
            '1001': {'status': 'pass', 'meaning': 'Invoice accepted'},
            '1002': {'status': 'pass', 'meaning': 'Invoice accepted with warnings'},
            '2001': {'status': 'fail', 'meaning': 'Invalid invoice format'},
            '2002': {'status': 'fail', 'meaning': 'Duplicate invoice'},
            '2003': {'status': 'fail', 'meaning': 'VAT calculation error'},
            '4100': {'status': 'fail', 'meaning': 'Business registration error'},
            '4101': {'status': 'fail', 'meaning': 'Timestamp validation failed'}
        }

        code_mapping = zatca_codes.get(status_code, {})
        base_status = code_mapping.get('status', status)

        prompt = f"""Interpret this ZATCA validation result in detail.

Status: {base_status}
Message: {zatca_message}
Status Code: {status_code or 'unknown'}

Provide interpretation in English:

Respond with JSON:
{{
    "status": "pass|warning|fail",
    "compliance_score": 85,
    "summary": "1 sentence summary of status",
    "user_friendly_message": "Message for business user explaining what this means",
    "technical_explanation": "Technical explanation of the result",
    "can_resubmit": true|false,
    "confidence": 0.95
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{status_code}: {zatca_message}",
                prompt=prompt,
                model=self.model,
                temperature=0.2
            )

            result = self._parse_json_response(response)
            score = result.get('compliance_score', 50)
            if base_status == 'pass':
                score = 100
            elif base_status == 'warning':
                score = 75
            else:
                score = 25

            return {
                'status': result.get('status', base_status),
                'score': score,
                'user_message': result.get('user_friendly_message', zatca_message),
                'technical': result.get('technical_explanation', ''),
                'can_resubmit': result.get('can_resubmit', True),
                'confidence': result.get('confidence', 0.7)
            }
        except Exception as e:
            logger.warning(f"Result interpretation failed: {str(e)}")
            return {
                'status': base_status,
                'score': 50 if base_status == 'warning' else (100 if base_status == 'pass' else 25),
                'user_message': zatca_message,
                'can_resubmit': base_status != 'pass',
                'confidence': 0.5
            }

    def _identify_violations(
        self,
        interpretation: Dict[str, Any],
        error_details: Optional[str],
        language: str
    ) -> Dict[str, Any]:
        """Identify specific compliance violations."""
        prompt = f"""Identify ZATCA compliance violations from this result:

Status: {interpretation['status']}
Message: {interpretation['user_message']}
Error Details: {error_details or 'none'}

Identify violations in {language}:

Respond with JSON:
{{
    "violations": [
        {{"violation": "description", "severity": "critical|high|medium|low", "article": "ZATCA article/requirement"}}
    ],
    "categories": ["vat_calculation", "invoice_format", "timestamp", "registration"],
    "critical_issues": ["issue1"],
    "total_issues": 2
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{interpretation['status']}: {error_details or interpretation['user_message']}",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return {
                'issues': result.get('violations', []),
                'categories': result.get('categories', []),
                'critical': result.get('critical_issues', []),
                'total_count': result.get('total_issues', 0)
            }
        except Exception as e:
            logger.warning(f"Violation identification failed: {str(e)}")
            return {
                'issues': [],
                'categories': [],
                'critical': [],
                'total_count': 0
            }

    def _assess_compliance_risk(
        self,
        violations: Dict[str, Any],
        validation_status: str,
        language: str
    ) -> Dict[str, Any]:
        """Assess compliance and business risk."""
        prompt = f"""Assess business and compliance risk from these violations:

Validation Status: {validation_status}
Issues Found: {len(violations['issues'])}
Critical Issues: {len(violations['critical'])}

Respond with JSON:
{{
    "business_risk_level": "critical|high|medium|low",
    "regulatory_penalty_risk": "high|medium|low",
    "filing_impact": "cannot_file|delayed_filing|standard_filing",
    "tax_liability_adjustment_possible": true|false,
    "audit_trigger_probability": "high|medium|low",
    "cash_impact": "immediate|30_days|90_days",
    "recommended_escalation": "cfo|legal|zatca_consultant|none"
}}
"""

        try:
            response = self.client.text_extract(
                text=f"Risk assessment for {len(violations['issues'])} violations",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return result
        except Exception as e:
            logger.warning(f"Risk assessment failed: {str(e)}")
            return {
                'business_risk_level': 'medium',
                'regulatory_penalty_risk': 'medium',
                'audit_trigger_probability': 'medium'
            }

    def _generate_remediation_plan(
        self,
        violations: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Generate step-by-step remediation plan."""
        prompt = f"""Create detailed remediation plan for these ZATCA violations in {language}:

Issues: {json.dumps(violations['issues'][:3], ensure_ascii=False)}

Provide in {language}:

Respond with JSON:
{{
    "steps": [
        {{"step": 1, "action": "specific action", "owner": "who does this", "timeline": "when"}}
    ],
    "priority": "critical|high|normal",
    "estimated_hours": 4,
    "article_references": ["ZAT.001", "ZAT.002"],
    "success_criteria": ["verification method1"]
}}
"""

        try:
            response = self.client.text_extract(
                text=f"Remediation for {len(violations['issues'])} violations",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return {
                'steps': result.get('steps', []),
                'priority': result.get('priority', 'high'),
                'estimated_hours': result.get('estimated_hours', 8),
                'article_references': result.get('article_references', [])
            }
        except Exception as e:
            logger.warning(f"Remediation plan generation failed: {str(e)}")
            return {
                'steps': [],
                'priority': 'high',
                'estimated_hours': 8,
                'article_references': []
            }

    def _check_resubmission_required(
        self,
        violations: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> bool:
        """Check if invoice resubmission is required."""
        # Resubmission required if there are critical issues or failures
        critical_count = len(violations.get('critical', []))
        return critical_count > 0 or len(violations['issues']) > 0

    def _assess_severity_level(self, violations: Dict[str, Any]) -> str:
        """Assess overall severity of violations."""
        if violations['critical']:
            return 'critical'
        
        high_count = sum(
            1 for v in violations['issues']
            if isinstance(v, dict) and v.get('severity') == 'high'
        )
        if high_count > 0:
            return 'high'
        
        medium_count = sum(
            1 for v in violations['issues']
            if isinstance(v, dict) and v.get('severity') == 'medium'
        )
        if medium_count > 0:
            return 'medium'
        
        return 'low'

    def _map_zatca_requirements(
        self,
        violations: Dict[str, Any]
    ) -> List[str]:
        """Map violations to ZATCA requirements."""
        requirements = {
            'vat_calculation': 'VAT must be calculated according to Saudi VAT law',
            'invoice_format': 'Invoice must contain all mandatory fields',
            'timestamp': 'Timestamps must be in UTC ISO 8601 format',
            'registration': 'Business registration must be valid with ZATCA',
            'duplicate': 'Invoices must be unique - no duplicates allowed',
            'settlement': 'Invoice must be issued within 30 days of supply'
        }

        mapped_requirements = []
        for category in violations.get('categories', []):
            if category in requirements:
                mapped_requirements.append(requirements[category])

        return mapped_requirements[:5]  # Return top 5

    def _generate_next_actions(
        self,
        interpretation: Dict[str, Any],
        violations: Dict[str, Any],
        resubmission_needed: bool,
        language: str
    ) -> List[str]:
        """Generate next action items."""
        actions = []

        if resubmission_needed:
            actions.append("Correct invoice errors and resubmit to ZATCA")
        
        if violations['critical']:
            actions.append("Escalate to compliance team immediately")
        
        if 'vat_calculation' in violations.get('categories', []):
            actions.append("Review VAT calculations with finance team")
        
        if 'registration' in violations.get('categories', []):
            actions.append("Verify business registration status with ZATCA")

        if len(actions) == 0:
            actions.append("Monitor invoice status")

        return actions[:3]  # Return top 3

    def _calculate_resubmission_deadline(
        self,
        violations: Dict[str, Any]
    ) -> Optional[str]:
        """Calculate deadline for resubmission if required."""
        if violations['critical']:
            # Critical issues require immediate (24 hours)
            from datetime import timedelta
            deadline = datetime.utcnow() + timedelta(days=1)
            return deadline.isoformat()
        
        if violations['issues']:
            # Non-critical issues require 5 business days
            from datetime import timedelta
            deadline = datetime.utcnow() + timedelta(days=5)
            return deadline.isoformat()
        
        return None

    def _get_similar_issues_history(
        self,
        violations: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Get history of similar issues (from database in production)."""
        # In production, query historical anomalies
        return []

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                if end > start:
                    return json.loads(response[start:end].strip())
            elif '```' in response:
                start = response.find('```') + 3
                end = response.find('```', start)
                if end > start:
                    return json.loads(response[start:end].strip())
            logger.warning(f"Failed to parse ZATCA response: {response[:100]}")
            return {}
