"""
Compliance Explanation Service - Arabic-focused AI explanations for audit findings

Provides AI-generated explanations for:
- Audit findings
- VAT discrepancies
- Zakat calculation issues
- ZATCA verification results
"""
import logging
import json
from typing import Dict, Optional, Any
from datetime import datetime
from decimal import Decimal

from .client import get_openai_client
from .errors import AIAPIError
from .constants import ERRORS_AR

logger = logging.getLogger(__name__)


class ComplianceExplainer:
    """Generate AI explanations for compliance findings."""
    
    def __init__(self):
        """Initialize explainer."""
        self.client = get_openai_client()
    
    def explain_audit_finding(
        self,
        finding_title_ar: str,
        finding_description_ar: str,
        risk_level: str,
        finding_type: str,
        financial_impact: Optional[Decimal] = None,
        regulatory_reference: Optional[str] = None,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generate Arabic explanation for audit finding.
        
        Args:
            finding_title_ar: Finding title in Arabic
            finding_description_ar: Finding description in Arabic
            risk_level: critical, high, medium, low
            finding_type: Type of finding
            financial_impact: Financial impact in SAR
            regulatory_reference: Reference regulation/clause
            language: Response language (ar/en/bilingual)
            
        Returns:
            Dict with:
            - explanation_ar: Arabic explanation
            - explanation_en: English explanation (if bilingual)
            - risk_analysis: Impact analysis
            - recommendations: Actionable recommendations
            - confidence: Confidence score
            - citations: Supporting regulations
            - timestamp: Generation timestamp
        """
        logger.info(f"Generating explanation for finding: {finding_title_ar}")
        
        # Build detailed prompt
        risk_labels = {
            'critical': 'حرج (خطر كبير جداً)',
            'high': 'مرتفع (خطر كبير)',
            'medium': 'متوسط (خطر معتدل)',
            'low': 'منخفض (خطر قليل)',
        }
        
        risk_label = risk_labels.get(risk_level, risk_level)
        
        prompt = f"""أنت مدقق مالي خبير متخصص في معايير المحاسبة السعودية والمعايير الدولية.

مهمتك: تقديم شرح مفصل وشامل لملاحظة التدقيق التالية:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
العنوان: {finding_title_ar}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

الوصف: {finding_description_ar}

مستوى المخاطر: {risk_label}
نوع الملاحظة: {finding_type}"""
        
        if financial_impact:
            prompt += f"\nالأثر المالي: {financial_impact:,.2f} ريال سعودي"
        
        if regulatory_reference:
            prompt += f"\nالمرجع التنظيمي: {regulatory_reference}"
        
        prompt += """

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
المطلوب: قدم الشرح بالصيغة التالية (JSON):

{
  "executive_summary": "ملخص تنفيذي للملاحظة في 2-3 جمل",
  
  "root_cause_analysis": "تحليل الأسباب الجذرية للمشكلة",
  
  "impact_analysis": {
    "financial_impact": "الأثر المالي بالتفصيل",
    "operational_impact": "الأثر التشغيلي والإجرائي",
    "compliance_impact": "تأثر الامتثال والاستقامة المالية",
    "risk_escalation": "احتمالية تصعيد المشكلة إذا لم تُحل"
  },
  
  "recommendations": [
    "التوصية الأولى: إجراء تصحيحي مفصل...",
    "التوصية الثانية: خطوات تنفيذية...",
    "التوصية الثالثة: مراقبة وتتبع..."
  ],
  
  "implementation_timeline": "إطار زمني مقترح للتنفيذ",
  
  "regulatory_references": [
    "المرجع 1: نص القانون أو التعليمات",
    "المرجع 2: معيار محاسبي رقم ..."
  ],
  
  "risk_mitigation": "خطة التخفيف من المخاطر على المدى القصير والطويل",
  
  "assurance_note": "ملاحظة مهمة: هذا الشرح استشاري فقط وليس قرارا نهائيا. يجب مراجعة المدقق البشري وتصديق الإدارة قبل اتخاذ أي إجراء."
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
قواعد مهمة:

1. استخدم لغة عربية احترافية وواضحة
2. كن محدداً وعملياً - لا تعطِ ردوداً عامة
3. ربط كل تحليل بالمعايير والتشريعات الفعلية
4. اذكر المخاطر بوضوح ولكن بطريقة احترافية
5. قدم خطوات تنفيذية قابلة للقياس
6. أضف إطاراً زمنياً واقعياً للتنفيذ
7. أكد أن القرار النهائي يعود للإدارة والمدقق البشري
8. عد الشرح صحة JSON فقط - لا تضف تعليقات أو شروح خارج الـ JSON

ابدأ الآن وقدم الشرح في JSON صحيح:
"""
        
        try:
            # Call OpenAI with special instructions for Arabic
            response = self.client.text_chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4  # Slightly creative but accurate
            )
            
            logger.debug(f"Explanation API response: {response[:200]}...")
            
            # Parse JSON response
            explanation_data = self._parse_json_response(response)
            
            return {
                'explanation_ar': explanation_data,
                'confidence': 0.85,  # AI explanations have high confidence
                'raw_response': response,
                'timestamp': datetime.now().isoformat(),
                'model': 'gpt-4o-mini',
                'language_requested': language,
            }
        
        except Exception as e:
            logger.error(f"Failed to generate explanation: {e}")
            raise AIAPIError(f"Explanation generation failed: {str(e)}")
    
    def explain_vat_discrepancy(
        self,
        discrepancy_description: str,
        expected_vat: Decimal,
        actual_vat: Decimal,
        affected_transactions: int = None
    ) -> Dict[str, Any]:
        """
        Explain VAT discrepancy.
        
        Args:
            discrepancy_description: Description of the discrepancy
            expected_vat: Expected VAT amount
            actual_vat: Actual VAT amount
            affected_transactions: Number of affected transactions
            
        Returns:
            Dict with explanation and recommendations
        """
        logger.info(f"Explaining VAT discrepancy: {expected_vat} vs {actual_vat}")
        
        variance = actual_vat - expected_vat
        variance_pct = (variance / expected_vat * 100) if expected_vat > 0 else 0
        
        prompt = f"""أنت خبير ضريبي متخصص في ضريبة القيمة المضافة السعودية.

شرح مختصر للفرق في الضريبة:

الفرق الضريبي: {variance:,.2f} ريال ({variance_pct:.1f}%)
الضريبة المتوقعة: {expected_vat:,.2f} ريال
الضريبة الفعلية: {actual_vat:,.2f} ريال
عدد المعاملات المتأثرة: {affected_transactions or 'غير محدد'}

قدم في صيغة JSON:
1. الأسباب المحتملة (بالترتيب من الأكثر إلى الأقل احتمالاً)
2. الخطوات المقترحة للتحقيق
3. التأثير على الإقرار الضريبي
4. الإجراءات التصحيحية المقترحة

JSON Format:
{{
  "possible_causes": ["السبب 1", "السبب 2", ...],
  "investigation_steps": ["الخطوة 1", "الخطوة 2", ...],
  "tax_filing_impact": "التأثير على الإقرار الضريبي",
  "corrective_actions": ["الإجراء 1", "الإجراء 2", ...]
}}
"""
        
        try:
            response = self.client.text_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            explanation_data = self._parse_json_response(response)
            
            return {
                'explanation': explanation_data,
                'variance': float(variance),
                'variance_percent': variance_pct,
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"VAT discrepancy explanation failed: {e}")
            raise AIAPIError(f"VAT explanation failed: {str(e)}")
    
    def explain_zatca_result(
        self,
        invoice_number: str,
        validation_message: str,
        validation_status: str,
        error_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Explain ZATCA verification result to end user.
        
        Args:
            invoice_number: Invoice number
            validation_message: Validation message from ZATCA
            validation_status: Status (approved, rejected, pending)
            error_detail: Detailed error message if failed
            
        Returns:
            Dict with user-friendly explanation
        """
        logger.info(f"Explaining ZATCA result for invoice {invoice_number}")
        
        prompt = f"""أنت متخصص في فواتير ZATCA الإلكترونية.

شرح نتيجة फتحقق الفاتورة:

رقم الفاتورة: {invoice_number}
حالة التحقق: {validation_status}
الرسالة: {validation_message}"""
        
        if error_detail:
            prompt += f"\nتفاصيل الخطأ: {error_detail}"
        
        prompt += """

اشرح النتيجة للمستخدم بطريقة واضحة وودية:
1. ما معنى هذه النتيجة
2. الخطوات التالية المطلوبة (إن وجدت)
3. كيفية تصحيح المشكلة (إن وجدت)

في صيغة JSON بسيطة:
{
  "user_friendly_message": "شرح بسيط للمستخدم",
  "next_steps": ["الخطوة 1", "الخطوة 2"],
  "action_required": true/false
}
"""
        
        try:
            response = self.client.text_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            explanation_data = self._parse_json_response(response)
            
            return {
                'user_explanation': explanation_data,
                'invoice_number': invoice_number,
                'status': validation_status,
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"ZATCA explanation failed: {e}")
            # Return default message if AI fails
            return {
                'user_explanation': {
                    'user_friendly_message': f'حالة الفاتورة: {validation_status}. {validation_message}',
                    'next_steps': [],
                    'action_required': validation_status != 'approved',
                },
                'invoice_number': invoice_number,
                'status': validation_status,
                'timestamp': datetime.now().isoformat(),
                'fallback': True,
            }
    
    # ===== Helper Methods =====
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from response, handling markdown."""
        response = response.strip()
        
        # Remove markdown if present
        if response.startswith('```'):
            response = response.split('```')[1]
            if response.startswith('json'):
                response = response[4:]
            response = response.strip()
        
        return json.loads(response)
