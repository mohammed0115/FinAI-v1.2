"""
Extended Explanations AI Module

Provides comprehensive, auditor-friendly explanations of financial data,
compliance findings, and AI-driven recommendations.

Features:
- Executive summaries
- Detailed finding analysis
- Impact assessments
- Audit-ready documentation
- Multi-language support
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.ai.client import get_openai_client
from core.ai.errors import AIAPIError

logger = logging.getLogger(__name__)


class ExtendedExplanationAI:
    """
    Generates comprehensive, auditor-focused explanations for financial
    data, findings, and recommendations.
    """

    def __init__(self):
        self.client = get_openai_client()
        self.model = 'gpt-4o-mini'

    def generate_audit_report(
        self,
        finding_title: str,
        finding_description: str,
        finding_type: str,
        severity: str,
        affected_amount: Optional[float] = None,
        affected_transactions: int = 0,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit report for a finding.

        Args:
            finding_title: Title of finding (Arabic preferred)
            finding_description: Detailed description
            finding_type: Type of finding (vat, duplicate, control, etc.)
            severity: Severity level (critical, high, medium, low)
            affected_amount: Financial impact
            affected_transactions: Number of affected transactions
            language: Report language ('ar' or 'en')

        Returns:
            Audit report with:
            - executive_summary
            - detailed_analysis
            - root_cause_analysis
            - impact_assessment
            - recommendations
            - implementation_timeline
            - responsible_party
            - audit_evidence
            - risk_matrix
            - remediation_tracking
        """
        try:
            start_time = datetime.utcnow()

            # Generate sections
            executive_summary = self._generate_executive_summary(
                finding_title, finding_description, severity, language
            )

            detailed_analysis = self._generate_detailed_analysis(
                finding_title, finding_description, finding_type, language
            )

            root_cause = self._analyze_root_cause(
                finding_description, finding_type, language
            )

            impact_assessment = self._assess_impact(
                finding_type, severity, affected_amount, affected_transactions, language
            )

            recommendations = self._generate_recommendations(
                finding_type, root_cause, severity, language
            )

            audit_evidence = self._compile_audit_evidence(
                finding_type, affected_transactions, language
            )

            risk_matrix = self._build_risk_matrix(
                severity, finding_type, affected_transactions
            )

            result = {
                'report_id': f"AR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                'finding_title': finding_title,
                'finding_type': finding_type,
                'severity': severity,
                'report_date': start_time.isoformat(),
                'executive_summary': executive_summary,
                'detailed_analysis': detailed_analysis,
                'root_cause_analysis': root_cause,
                'impact_assessment': impact_assessment,
                'financial_impact': {
                    'affected_amount': affected_amount,
                    'affected_transactions': affected_transactions,
                    'percentage_of_population': self._calculate_percentage(
                        affected_transactions
                    )
                },
                'recommendations': recommendations,
                'implementation_timeline': self._create_timeline(severity, recommendations),
                'responsible_party': self._identify_responsible_party(finding_type),
                'audit_evidence': audit_evidence,
                'risk_matrix': risk_matrix,
                'compliance_references': self._get_compliance_references(finding_type),
                'required_follow_up': severity in ['critical', 'high'],
                'management_response_required': True,
                'audit_trail': {
                    'created_at': start_time.isoformat(),
                    'version': '1.0',
                    'generator': 'ExtendedExplanationAI'
                },
                'language': language,
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000)
            }

            logger.info(f"Audit report generated: {finding_type} ({severity})")
            return result

        except Exception as e:
            logger.error(f"Audit report generation error: {str(e)}", exc_info=True)
            raise AIAPIError(f"Report generation failed: {str(e)}")

    def _generate_executive_summary(
        self,
        title: str,
        description: str,
        severity: str,
        language: str
    ) -> str:
        """Generate executive summary."""
        prompt = f"""Generate a concise executive summary for this audit finding in {language}.

Title: {title}
Description: {description}
Severity: {severity}

Requirements:
- 2-3 sentences maximum
- Clear and actionable
- Written for senior management
- In {language}

Respond with JSON:
{{
    "summary": "executive summary text in {language}"
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{title}: {description}",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return result.get('summary', description)
        except Exception as e:
            logger.warning(f"Executive summary generation failed: {str(e)}")
            return description

    def _generate_detailed_analysis(
        self,
        title: str,
        description: str,
        finding_type: str,
        language: str
    ) -> str:
        """Generate detailed analysis."""
        prompt = f"""Create detailed analysis of this audit finding in {language}.

Title: {title}
Type: {finding_type}
Description: {description}

Include in {language}:
1. What happened
2. How it was identified
3. Scope of issue
4. Deviation from policy/regulation

Respond with JSON:
{{
    "analysis": "detailed 3-4 paragraph analysis in {language}"
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{title}: {description}",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return result.get('analysis', description)
        except Exception as e:
            logger.warning(f"Detailed analysis generation failed: {str(e)}")
            return description

    def _analyze_root_cause(
        self,
        description: str,
        finding_type: str,
        language: str
    ) -> Dict[str, Any]:
        """Analyze root causes of finding."""
        prompt = f"""Perform root cause analysis of this finding in {language}.

Finding Type: {finding_type}
Description: {description}

Identify in {language}:
- Primary root cause
- Contributing factors
- Why controls failed
- Underlying issues

Respond with JSON:
{{
    "primary_cause": "main root cause in {language}",
    "contributing_factors": ["factor1", "factor2"],
    "control_failure": "why preventive controls didn't catch this",
    "systemic_issues": ["issue1"],
    "must_address": true|false
}}
"""

        try:
            response = self.client.text_extract(
                text=description,
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return {
                'primary_cause': result.get('primary_cause', 'Unknown'),
                'contributing_factors': result.get('contributing_factors', []),
                'control_failure_reason': result.get('control_failure', ''),
                'systemic_issues': result.get('systemic_issues', [])
            }
        except Exception as e:
            logger.warning(f"Root cause analysis failed: {str(e)}")
            return {
                'primary_cause': 'Root cause analysis pending',
                'contributing_factors': [],
                'control_failure_reason': ''
            }

    def _assess_impact(
        self,
        finding_type: str,
        severity: str,
        affected_amount: Optional[float],
        affected_transactions: int,
        language: str
    ) -> Dict[str, Any]:
        """Assess impact of finding."""
        impact_map = {
            'critical': 'severe',
            'high': 'significant',
            'medium': 'moderate',
            'low': 'minimal'
        }

        prompt = f"""Assess financial and operational impact in {language}:

Type: {finding_type}
Severity: {severity}
Affected Amount: {affected_amount or 'unknown'}
Transactions: {affected_transactions}

Assess impact in {language}:

Respond with JSON:
{{
    "financial_impact": "description of financial consequences",
    "operational_impact": "operational implications",
    "compliance_impact": "regulatory/compliance impact",
    "reputation_risk": "reputational implications",
    "stakeholder_impact": "who is affected and how"
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{finding_type} impact assessment",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return {
                'impact_level': impact_map.get(severity, 'moderate'),
                'financial_implications': result.get('financial_impact', ''),
                'operational_implications': result.get('operational_impact', ''),
                'compliance_implications': result.get('compliance_impact', ''),
                'reputational_risk': result.get('reputation_risk', 'Unknown'),
                'stakeholders_affected': result.get('stakeholder_impact', '')
            }
        except Exception as e:
            logger.warning(f"Impact assessment failed: {str(e)}")
            return {
                'impact_level': impact_map.get(severity, 'moderate'),
                'financial_implications': f'Impact assessment pending for {finding_type}'
            }

    def _generate_recommendations(
        self,
        finding_type: str,
        root_cause: Dict[str, Any],
        severity: str,
        language: str
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations."""
        prompt = f"""Generate specific, actionable recommendations in {language}:

Finding Type: {finding_type}
Root Cause: {root_cause.get('primary_cause', 'unknown')}
Severity: {severity}

Provide 4-6 recommendations in {language}:

Respond with JSON:
{{
    "recommendations": [
        {{"recommendation": "specific action", "priority": "critical|high|medium", "timeline": "1-month|3-months|etc"}}
    ]
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{finding_type} recommendations",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            return result.get('recommendations', [])
        except Exception as e:
            logger.warning(f"Recommendation generation failed: {str(e)}")
            return [
                {
                    'recommendation': f'Implement controls for {finding_type}',
                    'priority': 'high',
                    'timeline': '1-month'
                }
            ]

    def _create_timeline(
        self,
        severity: str,
        recommendations: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """Create implementation timeline."""
        if severity == 'critical':
            return {
                'immediate': 'Within 1 week',
                'short_term': '1-2 months',
                'medium_term': '3-4 months',
                'long_term': '6 months'
            }
        elif severity == 'high':
            return {
                'immediate': 'Within 2 weeks',
                'short_term': '1-3 months',
                'medium_term': '3-6 months',
                'long_term': 'TBD'
            }
        else:
            return {
                'short_term': '1-3 months',
                'medium_term': '3-6 months',
                'long_term': '6-12 months'
            }

    def _identify_responsible_party(self, finding_type: str) -> str:
        """Identify responsible party."""
        responsibility_map = {
            'vat': 'CFO / Tax Manager',
            'duplicate': 'AP Manager',
            'control': 'Process Owner',
            'compliance': 'Compliance Officer',
            'documentation': 'Records Manager',
            'system': 'IT Manager'
        }
        return responsibility_map.get(finding_type.lower(), 'Finance Manager')

    def _compile_audit_evidence(
        self,
        finding_type: str,
        transaction_count: int,
        language: str
    ) -> Dict[str, Any]:
        """Compile audit evidence."""
        return {
            'evidence_type': 'financial_documents',
            'sample_size': min(transaction_count, 25),  # Audit sample
            'documentation_method': 'electronic_records',
            'available_evidence': [
                'Original transaction documents',
                'System reports',
                'Exception logs',
                'Exception handling documentation'
            ] if transaction_count > 0 else [],
            'evidence_location': 'Document management system'
        }

    def _build_risk_matrix(
        self,
        severity: str,
        finding_type: str,
        transaction_count: int
    ) -> Dict[str, Any]:
        """Build risk assessment matrix."""
        likelihood_map = {
            'critical': 'Very High',
            'high': 'High',
            'medium': 'Medium',
            'low': 'Low'
        }

        impact_map = {
            'critical': 5,
            'high': 4,
            'medium': 3,
            'low': 2
        }

        likelihood_score = {'Very High': 5, 'High': 4, 'Medium': 3, 'Low': 2, 'Very Low': 1}
        l_score = likelihood_score.get(likelihood_map[severity], 3)
        i_score = impact_map[severity]
        risk_score = l_score * i_score

        return {
            'likelihood': likelihood_map[severity],
            'impact': severity.upper(),
            'risk_score': risk_score,
            'risk_rating': 'CRITICAL' if risk_score >= 20 else 'HIGH' if risk_score >= 12 else 'MEDIUM'
        }

    def _get_compliance_references(self, finding_type: str) -> List[str]:
        """Get relevant compliance references."""
        references = {
            'vat': ['ZATCA VAT Directive', 'KSA VAT Law', 'Invoice Requirement Regulation'],
            'duplicate': ['Internal Control Policy', 'Document Management Policy'],
            'compliance': ['ZATCA Requirements', 'Internal Policies'],
            'documentation': ['Record Retention Policy', 'Document Control Procedure']
        }
        return references.get(finding_type.lower(), ['Internal Policies'])

    def _calculate_percentage(self, transaction_count: int) -> str:
        """Calculate percentage of population affected."""
        if transaction_count == 0:
            return '0%'
        # In production, would calculate against total population
        return f'{min(transaction_count / 100 * 100, 100):.1f}%'

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
            logger.warning(f"Failed to parse explanation response")
            return {}
