"""
Phase 4: Anomaly Explanation Service

Uses OpenAI to generate natural language explanations for:
- Duplicate suspicions
- Anomaly causes
- Vendor risk factors
- Recommended reviewer actions

Falls back to rule-based explanations if OpenAI unavailable.
"""

import logging
import os
import requests
import json

from documents.models import ExtractedData, VendorRisk

logger = logging.getLogger(__name__)


class InvoiceAnomalyExplanationService:
    """Service for generating anomaly explanations"""
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_URL = 'https://api.openai.com/v1/chat/completions'
    MODEL = 'gpt-3.5-turbo'
    MAX_TOKENS = 500
    TIMEOUT = 5  # seconds
    
    def explain_duplicate_suspicion(self, extracted_data, matched_document=None):
        """Generate explanation for duplicate suspicion"""
        
        try:
            if not extracted_data.duplicate_score or extracted_data.duplicate_score < 60:
                return {
                    'explanation': 'No significant duplicate risk detected.',
                    'generated_by': 'rule_based',
                }
            
            prompt = f"""
            Explain why this invoice might be a duplicate. Be concise and actionable.
            
            Current Invoice:
            - Number: {extracted_data.invoice_number}
            - Vendor: {extracted_data.vendor_name}
            - Date: {extracted_data.invoice_date}
            - Amount: {extracted_data.total_amount} {extracted_data.currency}
            
            Duplicate Score: {extracted_data.duplicate_score}%
            
            {f'Matched Invoice: {matched_document.invoice_number} from {matched_document.vendor_name} on {matched_document.invoice_date}' if matched_document else ''}
            
            Provide a brief explanation (2-3 sentences) of the duplicate risk and recommend next steps.
            """
            
            result = self._call_openai(prompt)
            if result:
                return {
                    'explanation': result,
                    'generated_by': 'openai',
                    'duplicate_score': extracted_data.duplicate_score,
                }
        
        except Exception as e:
            logger.warning(f"OpenAI call failed for duplicate explanation: {str(e)}")
        
        # Fallback
        return self._fallback_duplicate_explanation(extracted_data, matched_document)
    
    def explain_anomalies(self, extracted_data, anomaly_flags):
        """Generate explanation for detected anomalies"""
        
        try:
            if not anomaly_flags:
                return {
                    'explanation': 'No anomalies detected.',
                    'generated_by': 'rule_based',
                }
            
            # Summarize anomalies
            anomaly_summary = ", ".join([f.get('type', '').replace('_', ' ') for f in anomaly_flags[:5]])
            
            prompt = f"""
            Explain the significance of these invoice anomalies:
            
            Invoice: {extracted_data.invoice_number}
            Vendor: {extracted_data.vendor_name}
            Amount: {extracted_data.total_amount} {extracted_data.currency}
            
            Anomalies detected:
            {chr(10).join([f"- {f.get('description', f.get('type', ''))}" for f in anomaly_flags[:5]])}
            
            Provide a brief analysis (2-3 sentences) of what these anomalies indicate and recommended actions.
            """
            
            result = self._call_openai(prompt)
            if result:
                return {
                    'explanation': result,
                    'generated_by': 'openai',
                    'anomaly_count': len(anomaly_flags),
                }
        
        except Exception as e:
            logger.warning(f"OpenAI call failed for anomaly explanation: {str(e)}")
        
        # Fallback
        return self._fallback_anomaly_explanation(anomaly_flags)
    
    def explain_vendor_risk(self, vendor_risk):
        """Generate explanation for vendor risk"""
        
        try:
            if not vendor_risk or vendor_risk.risk_score < 25:
                return {
                    'explanation': f'Vendor {vendor_risk.vendor_name} has low risk profile.',
                    'generated_by': 'rule_based',
                }
            
            prompt = f"""
            Analyze and explain the risk profile for this vendor:
            
            Vendor: {vendor_risk.vendor_name}
            Risk Score: {vendor_risk.risk_score}/100
            Risk Level: {vendor_risk.risk_level}
            
            Historical Issues:
            - Total invoices: {vendor_risk.total_invoices}
            - Duplicate suspicions: {vendor_risk.duplicate_suspicion_count}
            - Anomalies detected: {vendor_risk.anomaly_count}
            - Violations confirmed: {vendor_risk.violation_count}
            - Compliance failures: {vendor_risk.compliance_failure_count}
            
            Provide a brief assessment (2-3 sentences) of the vendor risk and recommended mitigation strategies.
            """
            
            result = self._call_openai(prompt)
            if result:
                return {
                    'explanation': result,
                    'generated_by': 'openai',
                    'risk_score': vendor_risk.risk_score,
                    'risk_level': vendor_risk.risk_level,
                }
        
        except Exception as e:
            logger.warning(f"OpenAI call failed for vendor risk explanation: {str(e)}")
        
        # Fallback
        return self._fallback_vendor_risk_explanation(vendor_risk)
    
    def generate_reviewer_recommendation(self, extracted_data):
        """Generate recommendation for reviewer"""
        
        try:
            # Build context
            issues = []
            
            if extracted_data.risk_level and extracted_data.risk_level.lower() in ['high', 'critical']:
                issues.append(f"High risk score: {extracted_data.risk_score}")
            
            if extracted_data.duplicate_score and extracted_data.duplicate_score >= 75:
                issues.append(f"Duplicate risk: {extracted_data.duplicate_score}%")
            
            if extracted_data.anomaly_score and extracted_data.anomaly_score >= 50:
                issues.append(f"Multiple anomalies detected (score: {extracted_data.anomaly_score})")
            
            if extracted_data.cross_document_findings.filter(severity='critical').exists():
                issues.append("Critical findings present")
            
            if not issues:
                return {
                    'recommendation': 'Invoice appears compliant. Proceed with standard processing.',
                    'action': 'approve',
                    'generated_by': 'rule_based',
                }
            
            issue_text = "\n".join(f"- {issue}" for issue in issues)
            
            prompt = f"""
            Recommend an action for this invoice based on detected issues:
            
            Invoice: {extracted_data.invoice_number}
            Vendor: {extracted_data.vendor_name}
            Amount: {extracted_data.total_amount} {extracted_data.currency}
            
            Issues flagged:
            {issue_text}
            
            Recommend whether this invoice should be:
            1. Approved (proceed)
            2. Reviewed (manual review recommended)
            3. Blocked (hold for investigation)
            
            Provide your recommendation (1-2 sentences) with reasoning.
            """
            
            result = self._call_openai(prompt)
            if result:
                # Parse recommendation to determine action
                action = 'review'  # Default
                if 'approve' in result.lower() or 'proceed' in result.lower():
                    action = 'approve'
                elif 'block' in result.lower() or 'hold' in result.lower() or 'investigate' in result.lower():
                    action = 'block'
                
                return {
                    'recommendation': result,
                    'action': action,
                    'generated_by': 'openai',
                }
        
        except Exception as e:
            logger.warning(f"OpenAI call failed for reviewer recommendation: {str(e)}")
        
        # Fallback
        return self._fallback_reviewer_recommendation(extracted_data)
    
    def _call_openai(self, prompt):
        """Call OpenAI API"""
        
        if not self.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.OPENAI_API_KEY}',
                'Content-Type': 'application/json',
            }
            
            payload = {
                'model': self.MODEL,
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a financial audit assistant. Provide concise, actionable analysis of invoice issues.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': self.MAX_TOKENS,
                'temperature': 0.7,
            }
            
            response = requests.post(
                self.OPENAI_API_URL,
                headers=headers,
                json=payload,
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                message = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return message.strip()
            else:
                logger.warning(f"OpenAI API error: {response.status_code} - {response.text}")
                return None
        
        except requests.Timeout:
            logger.warning("OpenAI API timeout")
            return None
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {str(e)}")
            return None
    
    def _fallback_duplicate_explanation(self, extracted_data, matched_document=None):
        """Fallback rule-based duplicate explanation"""
        
        score = extracted_data.duplicate_score or 0
        
        if score >= 90:
            explanation = (f"This invoice has {score}% similarity to another invoice. "
                          f"Likely duplicate - verify against records immediately.")
        elif score >= 75:
            explanation = (f"This invoice matches another on file ({score}% similarity). "
                          f"Recommend manual review for potential duplicate.")
        else:
            explanation = (f"Potential duplicate detected ({score}% match). "
                          f"Check if this is a resubmission.")
        
        return {
            'explanation': explanation,
            'generated_by': 'rule_based',
            'duplicate_score': extracted_data.duplicate_score,
        }
    
    def _fallback_anomaly_explanation(self, anomaly_flags):
        """Fallback rule-based anomaly explanation"""
        
        if not anomaly_flags:
            return {
                'explanation': 'No anomalies detected.',
                'generated_by': 'rule_based',
            }
        
        anomaly_types = set(f.get('type') for f in anomaly_flags)
        
        parts = []
        
        if 'potential_duplicate' in anomaly_types:
            parts.append("Duplicate detected")
        
        if 'amount_spike' in anomaly_types:
            parts.append("unusual amount spike")
        
        if 'vat_inconsistency' in anomaly_types:
            parts.append("VAT inconsistency")
        
        if 'suspicious_discount' in anomaly_types:
            parts.append("suspicious discount")
        
        if 'frequency_anomaly' in anomaly_types:
            parts.append("frequency spike")
        
        explanation = f"Detected: {', '.join(parts)}. Recommend review." if parts else "Anomalies detected. Review recommended."
        
        return {
            'explanation': explanation,
            'generated_by': 'rule_based',
            'anomaly_count': len(anomaly_flags),
        }
    
    def _fallback_vendor_risk_explanation(self, vendor_risk):
        """Fallback rule-based vendor risk explanation"""
        
        if vendor_risk.risk_score >= 75:
            explanation = (f"Vendor {vendor_risk.vendor_name} presents CRITICAL RISK. "
                          f"Has {vendor_risk.anomaly_count} anomalies and {vendor_risk.duplicate_suspicion_count} duplicate suspicions. "
                          f"Recommend investigation.")
        elif vendor_risk.risk_score >= 50:
            explanation = (f"Vendor {vendor_risk.vendor_name} presents HIGH RISK. "
                          f"Multiple issues detected. Enhanced review recommended.")
        elif vendor_risk.risk_score >= 25:
            explanation = (f"Vendor {vendor_risk.vendor_name} has MEDIUM RISK. "
                          f"Standard review process recommended.")
        else:
            explanation = (f"Vendor {vendor_risk.vendor_name} has LOW RISK. "
                          f"Proceed with normal processing.")
        
        return {
            'explanation': explanation,
            'generated_by': 'rule_based',
            'risk_score': vendor_risk.risk_score,
            'risk_level': vendor_risk.risk_level,
        }
    
    def _fallback_reviewer_recommendation(self, extracted_data):
        """Fallback rule-based reviewer recommendation"""
        
        # Determine action based on risk factors
        if extracted_data.risk_level and extracted_data.risk_level.lower() == 'critical':
            action = 'block'
            recommendation = "BLOCK: Critical risk indicators present. Hold for investigation."
        elif extracted_data.duplicate_score and extracted_data.duplicate_score >= 75:
            action = 'block'
            recommendation = "BLOCK: High duplicate risk. Verify against existing records."
        elif extracted_data.risk_level and extracted_data.risk_level.lower() in ['high', 'medium']:
            action = 'review'
            recommendation = f"REVIEW: Risk level is {extracted_data.risk_level}. Manual review recommended."
        else:
            action = 'approve'
            recommendation = "APPROVE: Invoice meets compliance requirements. Proceed with processing."
        
        return {
            'recommendation': recommendation,
            'action': action,
            'generated_by': 'rule_based',
        }


# Singleton instance
invoice_anomaly_explanation_service = InvoiceAnomalyExplanationService()

