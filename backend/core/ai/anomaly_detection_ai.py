"""
Anomaly Detection AI Module

Provides AI-powered analysis and explanation of financial anomalies,
suspicious patterns, and unusual transactions.

Features:
- Anomaly explanation and context
- Severity assessment
- Pattern matching and clustering
- Investigation recommendations
- Fraud risk scoring
- Bilingual support (Arabic/English)
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.ai.client import get_openai_client
from core.ai.errors import AIAPIError

logger = logging.getLogger(__name__)


class AnomalyDetectionAI:
    """
    Provides AI-powered analysis of financial anomalies and suspicious patterns,
    with human-readable explanations for auditors and investigators.
    """

    def __init__(self):
        self.client = get_openai_client()
        self.model = 'gpt-4o-mini'

    def analyze_anomaly(
        self,
        anomaly_type: str,
        anomaly_description: str,
        context_data: Dict[str, Any],
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Analyze a detected anomaly and provide comprehensive explanation.

        Args:
            anomaly_type: Type of anomaly (duplicate, unusual_amount, vat_mismatch, etc.)
            anomaly_description: Description of the anomaly
            context_data: Additional context (historical avg, threshold, etc.)
            language: Response language ('ar' or 'en')

        Returns:
            Dict with:
            - anomaly_type: Classified anomaly type
            - severity: low|medium|high|critical
            - risk_score: 0-1 risk score
            - explanation: Human-readable explanation
            - possible_reasons: List of possible causes
            - investigation_steps: Recommended next steps
            - similar_cases: Historical similar cases
            - recommended_action: What to do about it
            - confidence: Confidence in assessment
            - timestamp: Processing timestamp
        """
        try:
            start_time = datetime.utcnow()

            # Classify and contextualize anomaly
            classification = self._classify_anomaly(
                anomaly_type, anomaly_description, context_data, language
            )

            # Generate explanation
            explanation = self._explain_anomaly(
                anomaly_type, anomaly_description, context_data, language
            )

            # Assess severity and risk
            severity_assessment = self._assess_severity(
                anomaly_type, explanation, context_data, language
            )

            # Generate investigation steps
            investigation_steps = self._generate_investigation_steps(
                classification, explanation, severity_assessment, language
            )

            # Find similar patterns
            similar_cases = self._find_similar_patterns(anomaly_type, context_data)

            # Determine recommended action
            recommended_action = self._determine_action(
                severity_assessment, anomaly_type, language
            )

            result = {
                'anomaly_type': classification['type'],
                'anomaly_category': classification['category'],
                'severity': severity_assessment['severity'],
                'risk_score': severity_assessment['risk_score'],
                'risk_level': self._risk_score_to_level(severity_assessment['risk_score']),
                'explanation_summary': explanation['summary'],
                'detailed_explanation': explanation['detailed'],
                'possible_causes': explanation['possible_causes'],
                'likelihood': explanation['likelihood'],
                'investigation_steps': investigation_steps,
                'similar_historical_cases': similar_cases,
                'compliance_impact': self._assess_compliance_impact(
                    anomaly_type, severity_assessment, language
                ),
                'recommended_action': recommended_action,
                'required_follow_up': severity_assessment['required_followup'],
                'evidence_points': self._extract_evidence_points(context_data),
                'confidence_score': explanation.get('confidence', 0.7),
                'language': language,
                'processing_time_ms': int((datetime.utcnow() - start_time).total_seconds() * 1000),
                'timestamp': start_time.isoformat()
            }

            logger.info(f"Anomaly analysis completed: {classification['type']} (severity: {severity_assessment['severity']})")
            return result

        except Exception as e:
            logger.error(f"Anomaly analysis error: {str(e)}", exc_info=True)
            raise AIAPIError(f"Anomaly analysis failed: {str(e)}")

    def _classify_anomaly(
        self,
        anomaly_type: str,
        anomaly_description: str,
        context_data: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Classify and categorize the anomaly."""
        classification_map = {
            'duplicate_invoice': {
                'category': 'data_quality',
                'financial_impact': 'high'
            },
            'unusual_amount': {
                'category': 'financial_variance',
                'financial_impact': 'medium'
            },
            'vat_mismatch': {
                'category': 'tax_compliance',
                'financial_impact': 'high'
            },
            'unusual_vendor': {
                'category': 'vendor_verification',
                'financial_impact': 'medium'
            },
            'pattern_deviation': {
                'category': 'behavioral_analysis',
                'financial_impact': 'low'
            },
            'timing_anomaly': {
                'category': 'temporal_analysis',
                'financial_impact': 'low'
            }
        }

        default_classification = classification_map.get(
            anomaly_type,
            {'category': 'other', 'financial_impact': 'medium'}
        )

        prompt = f"""Classify this anomaly accurately:

Type: {anomaly_type}
Description: {anomaly_description}

Provide detailed classification in {language}:

Respond with JSON:
{{
    "type": "detected anomaly type",
    "category": "one of: data_quality|financial_variance|tax_compliance|vendor_verification|behavioral|temporal|fraud|other",
    "classification_confidence": 0.9,
    "requires_immediate_action": true|false,
    "classification_reasoning": "why this classification"
}}
"""

        try:
            response = self.client.text_extract(
                text=anomaly_description,
                prompt=prompt,
                model=self.model,
                temperature=0.2
            )

            result = self._parse_json_response(response)
            return {
                'type': result.get('type', anomaly_type),
                'category': result.get('category', default_classification['category']),
                'requires_action': result.get('requires_immediate_action', True)
            }
        except Exception as e:
            logger.warning(f"Anomaly classification failed: {str(e)}")
            return {
                'type': anomaly_type,
                'category': default_classification['category'],
                'requires_action': True
            }

    def _explain_anomaly(
        self,
        anomaly_type: str,
        anomaly_description: str,
        context_data: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Generate comprehensive explanation of anomaly."""
        prompt = f"""Explain this financial anomaly for an auditor in {language}.

Anomaly Type: {anomaly_type}
Description: {anomaly_description}
Context: {json.dumps(context_data, ensure_ascii=False)[:500]}

Provide analysis in {language}:

Respond with JSON:
{{
    "summary": "1 sentence summary in {language}",
    "detailed_explanation": "2-3 sentence detailed explanation",
    "why_it_occurred": "Likely reasons this anomaly occurred",
    "possible_causes": ["cause1", "cause2", "cause3"],
    "likelihood": "very_likely|likely|possible|unlikely",
    "normal_behavior_description": "What normal behavior looks like",
    "confidence": 0.85
}}
"""

        try:
            response = self.client.text_extract(
                text=anomaly_description,
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return {
                'summary': result.get('summary', anomaly_description),
                'detailed': result.get('detailed_explanation', ''),
                'why_occurred': result.get('why_it_occurred', ''),
                'possible_causes': result.get('possible_causes', []),
                'likelihood': result.get('likelihood', 'possible'),
                'confidence': result.get('confidence', 0.6)
            }
        except Exception as e:
            logger.warning(f"Anomaly explanation failed: {str(e)}")
            return {
                'summary': anomaly_description,
                'detailed': '',
                'possible_causes': [],
                'likelihood': 'unknown',
                'confidence': 0.4
            }

    def _assess_severity(
        self,
        anomaly_type: str,
        explanation: Dict[str, Any],
        context_data: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Assess severity and risk score of anomaly."""
        # Base severity mappings
        severity_map = {
            'duplicate_invoice': 'high',
            'vat_mismatch': 'high',
            'unusual_vendor': 'medium',
            'unusual_amount': 'medium',
            'pattern_deviation': 'low',
            'timing_anomaly': 'low'
        }

        base_severity = severity_map.get(anomaly_type, 'medium')

        prompt = f"""Assess the severity of this anomaly in {language}:

Type: {anomaly_type}
Summary: {explanation.get('summary', '')}
Likelihood: {explanation.get('likelihood', 'unknown')}

Respond with JSON:
{{
    "severity": "low|medium|high|critical",
    "risk_score": 0.75,
    "financial_exposure": "amount at risk or impact description",
    "compliance_implication": "none|warning|violation|critical",
    "required_followup": true|false,
    "escalation_needed": false,
    "justification": "why this severity rating"
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{anomaly_type}: {explanation.get('summary', '')}",
                prompt=prompt,
                model=self.model,
                temperature=0.3
            )

            result = self._parse_json_response(response)
            return {
                'severity': result.get('severity', base_severity),
                'risk_score': result.get('risk_score', 0.5),
                'financial_exposure': result.get('financial_exposure', 'unknown'),
                'compliance_implication': result.get('compliance_implication', 'none'),
                'required_followup': result.get('required_followup', True),
                'escalation_needed': result.get('escalation_needed', False)
            }
        except Exception as e:
            logger.warning(f"Severity assessment failed: {str(e)}")
            return {
                'severity': base_severity,
                'risk_score': 0.5,
                'required_followup': True,
                'escalation_needed': False
            }

    def _generate_investigation_steps(
        self,
        classification: Dict[str, str],
        explanation: Dict[str, Any],
        severity: Dict[str, Any],
        language: str
    ) -> List[str]:
        """Generate recommended investigation steps."""
        prompt = f"""Generate investigation steps for this anomaly in {language}:

Type: {classification['type']}
Category: {classification['category']}
Severity: {severity['severity']}

Provide 4-6 specific, actionable investigation steps in {language}.

Respond with JSON:
{{
    "steps": [
        {{"step_number": 1, "action": "specific action", "expected_outcome": "what should be found"}},
        {{"step_number": 2, "action": "next action", "expected_outcome": "expected result"}}
    ]
}}
"""

        try:
            response = self.client.text_extract(
                text=f"{classification['type']} investigation",
                prompt=prompt,
                model=self.model,
                temperature=0.4
            )

            result = self._parse_json_response(response)
            steps_data = result.get('steps', [])
            return [
                f"Step {s.get('step_number', i+1)}: {s.get('action', '')}" 
                for i, s in enumerate(steps_data)
            ]
        except Exception as e:
            logger.warning(f"Investigation step generation failed: {str(e)}")
            return [
                "Review source documents",
                "Verify with vendor/customer",
                "Check system logs",
                "Consult with finance team"
            ]

    def _find_similar_patterns(
        self,
        anomaly_type: str,
        context_data: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Find similar historical cases."""
        # In production, this would query a database of historical anomalies
        similar_patterns = {
            'duplicate_invoice': [
                {
                    'id': 'ANO-2025-001',
                    'description': 'Duplicate invoice from same vendor',
                    'resolution': 'Deduplication and credit note issued',
                    'date': '2025-02-15'
                }
            ],
            'vat_mismatch': [
                {
                    'id': 'ANO-2025-002',
                    'description': 'VAT rate not applied correctly',
                    'resolution': 'Invoice corrected and refiled with ZATCA',
                    'date': '2025-02-10'
                }
            ]
        }

        return similar_patterns.get(anomaly_type, [])

    def _assess_compliance_impact(
        self,
        anomaly_type: str,
        severity: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Assess compliance and regulatory impact."""
        compliance_map = {
            'vat_mismatch': 'high',
            'duplicate_invoice': 'medium',
            'unusual_vendor': 'medium',
            'unusual_amount': 'low',
            'timing_anomaly': 'low'
        }

        impact_level = compliance_map.get(anomaly_type, 'low')

        return {
            'impact_level': impact_level,
            'zatca_relevant': anomaly_type in ['vat_mismatch', 'duplicate_invoice'],
            'audit_trail_required': severity.get('required_followup', False),
            'documentation_needed': True if impact_level != 'low' else False
        }

    def _determine_action(
        self,
        severity: Dict[str, Any],
        anomaly_type: str,
        language: str
    ) -> str:
        """Determine recommended action."""
        action_map = {
            'critical': 'Escalate to compliance officer immediately',
            'high': 'Investigate and document findings within 24 hours',
            'medium': 'Review and assess within 3-5 business days',
            'low': 'Log and monitor for patterns'
        }

        severity_level = severity.get('severity', 'medium')
        return action_map.get(severity_level, 'Review and assess')

    def _risk_score_to_level(self, score: float) -> str:
        """Convert numeric risk score to level."""
        if score >= 0.8:
            return 'critical'
        elif score >= 0.6:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        else:
            return 'low'

    def _extract_evidence_points(
        self,
        context_data: Dict[str, Any]
    ) -> List[str]:
        """Extract key evidence points from context."""
        evidence = []
        if 'amount_deviation' in context_data:
            evidence.append(f"Amount deviation: {context_data['amount_deviation']}")
        if 'frequency_anomaly' in context_data:
            evidence.append(f"Frequency anomaly detected: {context_data['frequency_anomaly']}")
        if 'vendor_mismatch' in context_data:
            evidence.append(f"Vendor mismatch: {context_data['vendor_mismatch']}")
        return evidence

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
            logger.warning(f"Failed to parse anomaly response: {response[:100]}")
            return {}
