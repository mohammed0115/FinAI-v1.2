"""
AI Explanation Service - خدمة الشروحات الذكية
LLM-based Arabic explanation generation for audit findings

SCOPE: ADVISORY ONLY - Non-decision-making explanations
- LLM output is logged with confidence for audit trail
- Human review is REQUIRED before any action
- No automatic scoring or decision changes
- Arabic-first output with full traceability
"""
import os
import uuid
import logging
import hashlib
from datetime import datetime
from typing import Dict, Optional
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Risk level translations
RISK_LEVEL_AR = {
    'critical': 'حرج',
    'high': 'مرتفع',
    'medium': 'متوسط',
    'low': 'منخفض',
}

# Finding type translations
FINDING_TYPE_AR = {
    'compliance': 'امتثال',
    'accuracy': 'دقة',
    'documentation': 'توثيق',
    'internal_control': 'رقابة داخلية',
    'fraud_risk': 'خطر احتيال',
    'calculation_error': 'خطأ حسابي',
}


class AIExplanationService:
    """
    خدمة توليد الشروحات الذكية لنتائج التدقيق
    AI-powered explanation generation for audit findings
    
    IMPORTANT COMPLIANCE NOTES:
    - All explanations are ADVISORY ONLY
    - Human review is REQUIRED before any action
    - No automatic decisions based on LLM output
    - Full audit trail maintained
    """
    
    def __init__(self):
        self.api_key = os.environ.get('EMERGENT_LLM_KEY', '')
        self._chat = None
        
    def _get_chat(self, session_id: str):
        """Initialize LLM chat with Arabic-first system message"""
        from emergentintegrations.llm.chat import LlmChat
        
        system_message = """أنت مدقق مالي خبير متخصص في معايير المحاسبة السعودية والمعايير الدولية.
        
مهمتك هي تقديم شروحات واضحة ومفصلة باللغة العربية لنتائج التدقيق المالي.

قواعد مهمة:
1. جميع الشروحات استشارية فقط وليست قرارات نهائية
2. يجب مراجعة المدقق البشري قبل اتخاذ أي إجراء
3. استخدم لغة مهنية ودقيقة
4. اربط الملاحظات بالأنظمة واللوائح ذات الصلة
5. قدم توصيات عملية قابلة للتنفيذ
6. لا تتخذ قرارات نهائية - دورك استشاري فقط

تنسيق الإجابة:
- ابدأ بملخص موجز للملاحظة
- اشرح الأثر المحتمل
- قدم التوصيات المقترحة
- أضف المراجع التنظيمية إن وجدت
- اختم بتأكيد أن القرار النهائي يعود للمدقق البشري"""
        
        chat = LlmChat(
            api_key=self.api_key,
            session_id=session_id,
            system_message=system_message
        ).with_model("gemini", "gemini-3-flash-preview")
        
        return chat
    
    async def generate_explanation_async(
        self,
        finding_id: str,
        title_ar: str,
        description_ar: str,
        risk_level: str,
        finding_type: str,
        financial_impact: Optional[Decimal] = None,
        regulatory_reference: Optional[str] = None,
    ) -> Dict:
        """
        توليد شرح ذكي لنتيجة التدقيق
        Generate AI explanation for an audit finding
        
        Returns:
            Dict with explanation, confidence, and audit trail
        """
        from emergentintegrations.llm.chat import UserMessage
        
        start_time = timezone.now()
        session_id = f"finding-{finding_id}-{uuid.uuid4().hex[:8]}"
        
        try:
            chat = self._get_chat(session_id)
            
            # Build the prompt
            risk_ar = RISK_LEVEL_AR.get(risk_level, risk_level)
            type_ar = FINDING_TYPE_AR.get(finding_type, finding_type)
            
            prompt = f"""قم بتحليل وشرح نتيجة التدقيق التالية:

العنوان: {title_ar}
الوصف: {description_ar}
مستوى المخاطر: {risk_ar}
نوع الملاحظة: {type_ar}
"""
            
            if financial_impact:
                prompt += f"الأثر المالي: {financial_impact:,.2f} ريال سعودي\n"
            
            if regulatory_reference:
                prompt += f"المرجع التنظيمي: {regulatory_reference}\n"
            
            prompt += """
قدم شرحاً مفصلاً يتضمن:
1. تحليل الملاحظة
2. الأثر المحتمل على المنشأة
3. التوصيات المقترحة
4. الإجراءات التصحيحية الممكنة

تذكر: هذا الشرح استشاري فقط ويتطلب مراجعة المدقق البشري."""

            # Send message to LLM
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            end_time = timezone.now()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Generate audit trail hash
            audit_hash = self._generate_audit_hash(
                finding_id, prompt, response, str(end_time)
            )
            
            # Log the generation
            logger.info(
                f"AI explanation generated for finding {finding_id} | "
                f"Risk: {risk_level} | Processing: {processing_time_ms}ms"
            )
            
            return {
                'success': True,
                'explanation_ar': response,
                'confidence_score': 85,  # Gemini doesn't provide confidence, use default
                'confidence_level': 'medium',
                'is_advisory': True,
                'requires_human_review': True,
                'model_used': 'gemini-3-flash-preview',
                'provider': 'gemini',
                'processing_time_ms': processing_time_ms,
                'generated_at': end_time.isoformat(),
                'session_id': session_id,
                'audit_hash': audit_hash,
                'disclaimer_ar': 'هذا الشرح استشاري فقط ويتطلب مراجعة المدقق البشري قبل اتخاذ أي إجراء',
                'disclaimer_en': 'This explanation is advisory only and requires human auditor review before any action',
            }
            
        except Exception as e:
            logger.error(f"AI explanation generation failed for finding {finding_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'explanation_ar': None,
                'confidence_score': 0,
                'is_advisory': True,
                'requires_human_review': True,
                'generated_at': timezone.now().isoformat(),
            }
    
    def generate_explanation_sync(
        self,
        finding_id: str,
        title_ar: str,
        description_ar: str,
        risk_level: str,
        finding_type: str,
        financial_impact: Optional[Decimal] = None,
        regulatory_reference: Optional[str] = None,
    ) -> Dict:
        """
        Synchronous wrapper for async explanation generation
        """
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.generate_explanation_async(
                finding_id=finding_id,
                title_ar=title_ar,
                description_ar=description_ar,
                risk_level=risk_level,
                finding_type=finding_type,
                financial_impact=financial_impact,
                regulatory_reference=regulatory_reference,
            )
        )
    
    def _generate_audit_hash(
        self, finding_id: str, prompt: str, response: str, timestamp: str
    ) -> str:
        """Generate SHA-256 hash for audit trail integrity"""
        hash_input = f"{finding_id}|{prompt}|{response}|{timestamp}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    
    def get_scope_documentation(self) -> Dict:
        """Return official scope documentation for AI explanations"""
        return {
            'service': 'FinAI AI Explanation Service',
            'purpose': 'Advisory explanations for audit findings',
            'scope_ar': '''
نطاق خدمة الشروحات الذكية:

ما تقوم به الخدمة:
• توليد شروحات باللغة العربية لنتائج التدقيق
• تقديم تحليل استشاري للملاحظات
• اقتراح توصيات للإجراءات التصحيحية
• ربط الملاحظات بالمراجع التنظيمية

ما لا تقوم به الخدمة:
• لا تتخذ قرارات نهائية
• لا تغير درجات المخاطر تلقائياً
• لا تستبدل المراجعة البشرية
• لا تنفذ إجراءات تصحيحية
            ''',
            'scope_en': '''
AI Explanation Service Scope:

What it DOES:
• Generate Arabic explanations for audit findings
• Provide advisory analysis of findings
• Suggest recommendations for corrective actions
• Link findings to regulatory references

What it does NOT do:
• Does NOT make final decisions
• Does NOT automatically change risk scores
• Does NOT replace human review
• Does NOT execute corrective actions
            ''',
            'compliance_requirements': [
                'Human review required before any action',
                'All outputs are advisory only',
                'Full audit trail maintained',
                'No automatic decision-making',
            ],
            'disclaimer_ar': 'جميع الشروحات استشارية فقط وتتطلب مراجعة المدقق البشري',
            'disclaimer_en': 'All explanations are advisory only and require human auditor review',
        }


# Singleton instance
ai_explanation_service = AIExplanationService()
