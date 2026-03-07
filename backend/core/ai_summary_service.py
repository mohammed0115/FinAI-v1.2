"""
AI Summary Service - Generate AI-powered audit summaries using OpenAI
"""
import logging
import json
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class AISummaryService:
    """Generate AI summaries for audit findings"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.temperature = float(settings.OPENAI_TEMPERATURE)
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
        
    def generate_audit_summary(self, extracted_data, findings):
        """
        Generate comprehensive AI audit summary in Arabic
        
        Args:
            extracted_data: ExtractedData instance
            findings: List of AuditFinding instances
            
        Returns:
            dict with executive_summary, key_risks, recommended_actions
        """
        try:
            if not self.client:
                logger.warning("OpenAI API key not configured")
                return self._default_summary(extracted_data, findings)
            
            # Prepare data for AI analysis
            invoice_data = {
                'invoice_number': extracted_data.invoice_number or 'N/A',
                'vendor_name': extracted_data.vendor_name or 'N/A',
                'invoice_date': str(extracted_data.invoice_date) if extracted_data.invoice_date else 'N/A',
                'total_amount': float(extracted_data.total_amount) if extracted_data.total_amount else 0,
                'tax_amount': float(extracted_data.tax_amount) if extracted_data.tax_amount else 0,
                'currency': extracted_data.currency or 'SAR',
            }
            
            findings_data = []
            for finding in findings:
                findings_data.append({
                    'type': finding.finding_type,
                    'risk_level': finding.risk_level,
                    'title_ar': finding.title_ar,
                    'description_ar': finding.description_ar,
                })
            
            # Build prompt
            prompt = self._build_prompt(invoice_data, findings_data)
            
            # Call OpenAI with new API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "أنت محلل مالي متخصص في التدقيق. قدم تحليل شامل بالعربية."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=1500,
            )
            
            summary_text = response.choices[0].message.content
            return self._parse_summary(summary_text)
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            return self._default_summary(extracted_data, findings)
    
    def _build_prompt(self, invoice_data, findings_data):
        """Build AI analysis prompt"""
        findings_text = "\n".join([
            f"- {f['title_ar']} ({f['risk_level']}): {f['description_ar']}"
            for f in findings_data
        ])
        
        prompt = f"""قم بتحليل الفاتورة التالية والنتائج المرفقة:

البيانات المستخرجة:
- رقم الفاتورة: {invoice_data['invoice_number']}
- البائع: {invoice_data['vendor_name']}
- التاريخ: {invoice_data['invoice_date']}
- المبلغ الإجمالي: {invoice_data['total_amount']} {invoice_data['currency']}
- الضريبة: {invoice_data['tax_amount']} {invoice_data['currency']}

نتائج التدقيق:
{findings_text}

أعد JSON فقط بالمفاتيح التالية، لا تضف أي نص خارج JSON:
{{
  "executive_summary": "ملخص تنفيذي موجز عن الفاتورة",
  "key_risks": ["خطر 1", "خطر 2", "خطر 3"],
  "recommended_actions": ["إجراء 1", "إجراء 2", "إجراء 3"],
  "final_status": "approved أو review أو rejected"
}}
key_risks و recommended_actions يجب أن تكون قوائم من النصوص فقط وليس كائنات.
"""
        return prompt
    
    def _parse_summary(self, summary_text):
        """Parse AI response and normalize to expected structure."""
        data = None
        try:
            if "{" in summary_text:
                start = summary_text.find("{")
                end = summary_text.rfind("}") + 1
                if start >= 0 and end > start:
                    data = json.loads(summary_text[start:end])
        except Exception:
            pass

        if not data:
            data = {
                "executive_summary": summary_text[:300],
                "key_risks": [summary_text[300:500]] if len(summary_text) > 300 else [],
                "recommended_actions": [summary_text[500:700]] if len(summary_text) > 500 else [],
                "final_status": "review"
            }

        # Fix typo: AI sometimes returns 'executor_summary' instead of 'executive_summary'
        if 'executor_summary' in data and 'executive_summary' not in data:
            data['executive_summary'] = data.pop('executor_summary')

        # Normalize key_risks: flatten dicts to readable strings
        raw_risks = data.get('key_risks', [])
        data['key_risks'] = [
            (r.get('description') or r.get('risk') or r.get('title') or str(r))
            if isinstance(r, dict) else str(r)
            for r in raw_risks
        ]

        # Normalize recommended_actions similarly
        raw_actions = data.get('recommended_actions', [])
        data['recommended_actions'] = [
            (r.get('action') or r.get('recommendation') or r.get('description') or str(r))
            if isinstance(r, dict) else str(r)
            for r in raw_actions
        ]

        return data
    
    def _default_summary(self, extracted_data, findings):
        """Generate default summary when AI is unavailable"""
        risk_levels = [f.risk_level for f in findings]
        highest_risk = "critical" if "critical" in risk_levels else \
                      "high" if "high" in risk_levels else \
                      "medium" if "medium" in risk_levels else "low"
        
        return {
            "executive_summary": f"فاتورة من {extracted_data.vendor_name or 'بائع غير معروف'} برقم {extracted_data.invoice_number or 'غير محدد'}",
            "key_risks": [f.title_ar for f in findings[:3]],
            "recommended_actions": [
                "مراجعة النتائج المرفقة",
                "التحقق من صحة البيانات المستخرجة",
                "متابعة الإجراءات المقترحة"
            ],
            "final_status": "review" if highest_risk in ["high", "critical"] else "approved"
        }


# Create singleton instance
ai_summary_service = AISummaryService()
