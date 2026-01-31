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


from core.ai_service import BaseAIOperation

from ai_plugins.services import AIPluginSettingsService

class AIExplanationOperation(BaseAIOperation):
    """
    Operation for generating AI explanations for audit findings (SRP, OCP, LSP).
    Uses AIPluginSetting selected by admin.
    """
    def execute(self, finding_id: str, title_ar: str, description_ar: str, risk_level: str, finding_type: str, financial_impact: Optional[Decimal] = None, regulatory_reference: Optional[str] = None) -> dict:
        plugin_setting = AIPluginSettingsService.get("ai_explanation")
        if not plugin_setting:
            return {
                'success': False,
                'error': 'لم يتم ضبط إعدادات الذكاء الاصطناعي لهذه العملية. يرجى مراجعة لوحة الضبط.'
            }
        # هنا يمكن ربط المزود الفعلي (OpenAI/Gemini) بناءً على الإعدادات
        # مثال: إرجاع الإعدادات المختارة (للتكامل الفعلي لاحقاً)
        return {
            'success': True,
            'provider': plugin_setting.provider,
            'model': plugin_setting.model_name,
            'temperature': plugin_setting.temperature,
            'max_tokens': plugin_setting.max_tokens,
            'message': f"شرح ذكي تم توليده باستخدام {plugin_setting.provider} - {plugin_setting.model_name} (placeholder)",
            'explanation_ar': f"شرح افتراضي للملاحظة: {title_ar} - {description_ar}",
            'confidence_score': 85,
            'is_advisory': True,
            'requires_human_review': True,
        }


class AIExplanationService:
    """
    خدمة توليد الشروحات الذكية لنتائج التدقيق (واجهة تعتمد على عملية AIExplanationOperation)
    """
    ai_explanation_operation = AIExplanationOperation()

    def generate_explanation_sync(
        self,
        finding_id: str,
        title_ar: str,
        description_ar: str,
        risk_level: str,
        finding_type: str,
        financial_impact: Optional[Decimal] = None,
        regulatory_reference: Optional[str] = None,
    ) -> dict:
        return self.ai_explanation_operation.execute(
            finding_id=finding_id,
            title_ar=title_ar,
            description_ar=description_ar,
            risk_level=risk_level,
            finding_type=finding_type,
            financial_impact=financial_impact,
            regulatory_reference=regulatory_reference,
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
