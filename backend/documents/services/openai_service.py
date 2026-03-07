"""
OpenAI Integration Service

Handles all OpenAI API calls for:
- Invoice summarization
- Audit findings generation
- Risk analysis
- Recommendation generation
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from documents.models import ExtractedData
from openai import OpenAI

logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for OpenAI API integration"""

    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = 'gpt-3.5-turbo'
    
    def is_configured(self) -> bool:
        """Check if OpenAI is properly configured"""
        return self.client is not None
    
    def generate_invoice_summary(
        self,
        extracted_data: ExtractedData,
        risk_level: str,
        anomalies: List[str]
    ) -> str:
        """Generate a summary of the invoice status"""
        
        if not self.is_configured():
            return self._generate_summary_fallback(extracted_data, risk_level, anomalies)
        
        try:
            prompt = f"""
            Analyze this invoice and provide a brief professional summary in English.
            
            Invoice Details:
            - Invoice Number: {extracted_data.invoice_number}
            - Vendor: {extracted_data.vendor_name}
            - Customer: {extracted_data.customer_name}
            - Date: {extracted_data.invoice_date}
            - Amount: {extracted_data.total_amount} {extracted_data.currency}
            - Risk Level: {risk_level}
            
            Issues Detected:
            {chr(10).join(f"- {a}" for a in anomalies) if anomalies else "- No issues detected"}
            
            Please provide:
            1. Overall assessment of the invoice
            2. Key observations
            3. Whether the invoice appears valid or requires careful review
            
            Keep the response concise (2-3 paragraphs).
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.warning(f"OpenAI API error: {e}")
            return self._generate_summary_fallback(extracted_data, risk_level, anomalies)
    
    def generate_audit_findings(
        self,
        extracted_data: ExtractedData,
        validation_results: Dict[str, Any],
        anomalies: List[str]
    ) -> str:
        """Generate detailed audit findings"""
        
        if not self.is_configured():
            return self._generate_findings_fallback(validation_results, anomalies)
        
        try:
            validation_summary = '\n'.join(
                [f"- {key}: {result['status']}" for key, result in validation_results.items()]
            )
            
            prompt = f"""
            Based on the following invoice validation results and detected anomalies, 
            provide detailed audit findings and recommendations.
            
            Validation Results:
            {validation_summary}
            
            Detected Anomalies:
            {chr(10).join(f"- {a}" for a in anomalies) if anomalies else "- None"}
            
            Invoice Amount: {extracted_data.total_amount} {extracted_data.currency}
            
            Please provide:
            1. Summary of key findings
            2. Any significant issues that need attention
            3. Whether manual invoice review is recommended
            
            Keep the response concise and professional.
            """
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.warning(f"OpenAI API error: {e}")
            return self._generate_findings_fallback(validation_results, anomalies)
    
    def _generate_summary_fallback(
        self,
        extracted_data: ExtractedData,
        risk_level: str,
        anomalies: List[str]
    ) -> str:
        """Generate summary without OpenAI (fallback)"""
        
        status = "appears to be valid" if risk_level == 'low' else "requires clarification"
        
        summary = f"""
        Invoice {extracted_data.invoice_number} from {extracted_data.vendor_name} 
        totaling {extracted_data.total_amount} {extracted_data.currency} {status}.
        """
        
        if anomalies:
            summary += f"\n\nDetected issues:\n" + '\n'.join(f"• {a}" for a in anomalies)
        
        summary += f"\n\nRisk Level: {risk_level.upper()}"
        
        return summary.strip()
    
    def _generate_findings_fallback(
        self,
        validation_results: Dict[str, Any],
        anomalies: List[str]
    ) -> str:
        """Generate findings without OpenAI (fallback)"""
        
        findings = []
        
        # Check validation results
        failed = [k for k, v in validation_results.items() if v['status'] == 'fail']
        if failed:
            findings.append(f"Failed validations: {', '.join(failed)}")
        
        # Check anomalies
        if anomalies:
            findings.append(f"Detected anomalies: {len(anomalies)} issue(s) found")
        
        if not findings:
            return "All validations passed. Invoice appears to be in order."
        
        return '\n'.join(findings)
