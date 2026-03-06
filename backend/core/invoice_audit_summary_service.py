# Invoice Audit Summary Service
# Uses OpenAI to generate executive summary, risks, and recommended actions
# Completes the audit workflow

import json
import logging
import os
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class InvoiceAuditSummaryService:
    """Generate OpenAI-based audit summary for invoices."""
    
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set - audit summaries will use fallback logic")
    
    def generate_audit_summary(
        self,
        extracted_json: dict,
        normalized_json: dict,
        validation_errors: list,
        validation_warnings: list,
        compliance_checks: list,
        risk_score: int,
        risk_level: str
    ) -> dict:
        """
        Generate comprehensive audit summary using OpenAI.
        
        Returns dict with:
        - executive_summary (str)
        - key_risks (list)
        - recommended_actions (list)
        - final_status (str)
        - requires_review (bool)
        """
        
        # If no API key, use rule-based summary
        if not self.api_key:
            return self._generate_fallback_summary(
                extracted_json, normalized_json, validation_errors,
                validation_warnings, compliance_checks, risk_score, risk_level
            )
        
        # Try OpenAI-based summary
        try:
            return self._call_openai_for_summary(
                extracted_json, normalized_json, validation_errors,
                validation_warnings, compliance_checks, risk_score, risk_level
            )
        except Exception as e:
            logger.error(f"OpenAI summary failed: {str(e)}, using fallback")
            return self._generate_fallback_summary(
                extracted_json, normalized_json, validation_errors,
                validation_warnings, compliance_checks, risk_score, risk_level
            )
    
    def _call_openai_for_summary(
        self,
        extracted_json: dict,
        normalized_json: dict,
        validation_errors: list,
        validation_warnings: list,
        compliance_checks: list,
        risk_score: int,
        risk_level: str
    ) -> dict:
        """Call OpenAI API to generate audit summary."""
        import requests
        
        # Prepare context for OpenAI
        validation_error_strs = [f"- {e.get('message', str(e))}" for e in validation_errors]
        validation_warning_strs = [f"- {w.get('message', str(w))}" for w in validation_warnings]
        compliance_check_strs = [f"- {c.get('check_name')}: {c.get('message')}" for c in compliance_checks]
        
        prompt = f"""You are an expert invoice auditor. Analyze this invoice audit data and provide:
1. Executive Summary (2-3 sentences about overall quality)
2. Key Risks (list top 3-5 risks)
3. Recommended Actions (list)
4. Final Status recommendation

INVOICE DATA:
Invoice: {extracted_json.get('invoice_number', 'N/A')}
Vendor: {extracted_json.get('vendor', {}).get('name', 'N/A')}
Customer: {extracted_json.get('customer', {}).get('name', 'N/A')}
Total: {normalized_json.get('total_amount', 'N/A')} {normalized_json.get('currency', 'N/A')}

VALIDATION STATUS:
Errors: {len(validation_errors)}
Warnings: {len(validation_warnings)}

VALIDATION ERRORS:
{chr(10).join(validation_error_strs) if validation_error_strs else '- None'}

VALIDATION WARNINGS:
{chr(10).join(validation_warning_strs) if validation_warning_strs else '- None'}

COMPLIANCE CHECKS ({len(compliance_checks)} total):
{chr(10).join(compliance_check_strs)}

RISK ASSESSMENT:
Risk Score: {risk_score}/100
Risk Level: {risk_level}

Please provide JSON response with keys: executive_summary, key_risks (array), recommended_actions (array), final_status"""
        
        # Call OpenAI (using requests, not openai library, for compatibility)
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",  # Cheaper than gpt-4o
                "messages": [
                    {"role": "system", "content": "You are an expert invoice auditor."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            },
            timeout=30
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Extract JSON from response
        try:
            # Try to parse as JSON directly
            summary_data = json.loads(content)
        except json.JSONDecodeError:
            # Extract JSON from markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
                summary_data = json.loads(content)
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                summary_data = json.loads(content)
            else:
                raise
        
        return {
            "executive_summary": summary_data.get("executive_summary", ""),
            "key_risks": summary_data.get("key_risks", []),
            "recommended_actions": summary_data.get("recommended_actions", []),
            "final_status": summary_data.get("final_status", "REVIEW_REQUIRED"),
            "requires_review": risk_level in ["High", "Critical"] or len(validation_errors) > 0,
            "generated_by": "openai"
        }
    
    def _generate_fallback_summary(
        self,
        extracted_json: dict,
        normalized_json: dict,
        validation_errors: list,
        validation_warnings: list,
        compliance_checks: list,
        risk_score: int,
        risk_level: str
    ) -> dict:
        """Generate summary using rule-based logic (no OpenAI)."""
        
        # Executive summary
        invoice_num = extracted_json.get('invoice_number', 'Unknown')
        vendor = extracted_json.get('vendor', {}).get('name', 'Unknown')
        
        if risk_level == "Critical":
            exec_summary = f"Invoice {invoice_num} from {vendor} has critical compliance issues requiring immediate review before posting."
        elif risk_level == "High":
            exec_summary = f"Invoice {invoice_num} from {vendor} has significant issues. Review recommended before posting."
        elif risk_level == "Medium":
            exec_summary = f"Invoice {invoice_num} from {vendor} has minor issues. Standard review recommended."
        else:
            exec_summary = f"Invoice {invoice_num} from {vendor} appears valid with minimal issues. Ready for processing."
        
        # Key risks
        key_risks = []
        failed_checks = [c for c in compliance_checks if c.get('status') != 'PASS']
        for check in failed_checks[:5]:  # Top 5
            key_risks.append(f"{check.get('check_name')}: {check.get('message')}")
        
        if validation_errors:
            key_risks.append(f"Validation errors: {len(validation_errors)} issue(s)")
        
        # Recommended actions
        recommended_actions = []
        if risk_level == "Critical":
            recommended_actions.append("URGENT: Review all critical compliance failures")
            recommended_actions.append("Verify vendor and customer information")
            recommended_actions.append("Contact vendor if discrepancies found")
            recommended_actions.append("Do not post to GL until issues resolved")
        
        if len(validation_errors) > 0:
            recommended_actions.append(f"Resolve {len(validation_errors)} validation error(s)")
        
        if risk_score >= 50:
            recommended_actions.append("Manual review required before approval")
        
        if not validation_errors and risk_level not in ["Critical", "High"]:
            recommended_actions.append("Approve and proceed to GL posting")
        
        # Final status
        if risk_level == "Critical":
            final_status = "BLOCKED_FOR_REVIEW"
        elif risk_level == "High":
            final_status = "REQUIRES_REVIEW"
        elif risk_level == "Medium":
            final_status = "REVIEW_RECOMMENDED"
        else:
            final_status = "READY_TO_POST" if not validation_errors else "REVIEW_RECOMMENDED"
        
        return {
            "executive_summary": exec_summary,
            "key_risks": key_risks,
            "recommended_actions": recommended_actions,
            "final_status": final_status,
            "requires_review": risk_level in ["High", "Critical"] or len(validation_errors) > 0,
            "generated_by": "rule_based"
        }


# Singleton instance
invoice_audit_summary_service = InvoiceAuditSummaryService()
