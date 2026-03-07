# ======================================================
# SOLID AI Operation Base (LSP, OCP)
# ======================================================
from abc import ABC, abstractmethod

class BaseAIOperation(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

# ======================================================
# SRP: Each operation in its own class
# ======================================================
class PromptManagerOperation(BaseAIOperation):
    def execute(self, admin_input: str):
        return {
            "success": True,
            "suggested_prompt_text": (
                "You are an AI assistant operating under strict enterprise governance. "
                "Your task is to help a SYSTEM ADMIN write deterministic, compliance-safe prompts. "
                "Do not perform financial analysis or decision-making."
            ),
            "output_schema_suggestion": {
                "success": "boolean",
                "result": "object or null",
                "blocked": "boolean",
                "reason": "string or null"
            },
            "validation_notes": (
                "Prompt must not request calculations, financial judgments, "
                "or business rule overrides."
            )
        }


from ai_plugins.services import AIPluginSettingsService

class DocumentVisionOperation(BaseAIOperation):
    def execute(self, image_url: str, document_type: str = "invoice"):
        # جلب إعدادات الذكاء الاصطناعي المختارة من الضبط (حسب الكود)
        plugin_setting = AIPluginSettingsService.get("document_vision")
        if plugin_setting:
            # إذا كان plugin مفعّل استخدم مزود AI
            return {
                "success": True,
                "provider": plugin_setting.provider,
                "model": plugin_setting.model_name,
                "temperature": plugin_setting.temperature,
                "max_tokens": plugin_setting.max_tokens,
                "message": f"Document processed using {plugin_setting.provider} - {plugin_setting.model_name} (AI plugin)"
            }
        else:
            # fallback إلى ML تقليدي (مثال: Tesseract أو أي خوارزمية ML)
            # هنا placeholder: يمكنك ربطه بـ ocr_service أو أي ML آخر
            return {
                "success": True,
                "provider": "Tesseract",
                "model": "Document Reader",
                "message": "Document processed using fallback ML (Tesseract or similar)"
            }

class CashFlowForecastOperation(BaseAIOperation):
    def execute(self, historical_data, periods=6):
        plugin_setting = AIPluginSettingsService.get("cash_flow_forecast")
        if plugin_setting:
            return [{
                "success": True,
                "provider": plugin_setting.provider,
                "model": plugin_setting.model_name,
                "message": f"Cash flow forecast using {plugin_setting.provider} (AI plugin)",
                "result": None
            }]
        else:
            return [{
                "success": True,
                "provider": "scikit-learn",
                "model": "Pattern Engine",
                "message": "Cash flow forecast using fallback ML (scikit-learn or similar)",
                "result": None
            }]

class AnomalyDetectionOperation(BaseAIOperation):
    def execute(self, transactions):
        plugin_setting = AIPluginSettingsService.get("anomaly")
        if plugin_setting:
            # إذا كان plugin مفعّل استخدم مزود AI
            return [{
                "success": True,
                "provider": plugin_setting.provider,
                "model": plugin_setting.model_name,
                "message": f"Anomaly detection using {plugin_setting.provider} (AI plugin)",
                "result": None  # هنا تضع نتيجة المزود الفعلي
            }]
        else:
            # fallback إلى ML تقليدي (مثال: PyOD)
            return [{
                "success": True,
                "provider": "PyOD",
                "model": "Risk Signal",
                "message": "Anomaly detection using fallback ML (PyOD or similar)",
                "result": None  # هنا تضع نتيجة ML الفعلي
            }]

class TrendAnalysisOperation(BaseAIOperation):
    def execute(self, financial_data, metrics=None):
        return []

class FinancialInsightsOperation(BaseAIOperation):
    def execute(self, organization_data):
        return []
import logging
import json
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ======================================================
# AI Operation Types (CRITICAL)
# ======================================================

class AIOperationType:
    PROMPT_MANAGEMENT = "prompt_management"
    FINANCIAL_EXECUTION = "financial_execution"


# ======================================================
# Hard Rules Gate Wrapper
# ======================================================

def _check_hard_rules_gate(
    payload: Dict = None,
    operation_type: str = AIOperationType.FINANCIAL_EXECUTION
) -> bool:
    """
    Central Hard Rules Gate with operation awareness
    """

    # ✅ Prompt Management is ALWAYS allowed
    if operation_type == AIOperationType.PROMPT_MANAGEMENT:
        return True

    try:
        from hard_rules.gate import hard_rules_gate

        result = hard_rules_gate(
            operation_type=operation_type,
            payload=payload
        )

        return result.get("allowed", False)

    except Exception as e:
        logger.error(f"Hard Rules Gate failed: {e}")
        # Fail-safe: block financial AI
        return False


# ======================================================
# AI Service (Facade)
# ======================================================


class AIService:
    """
    Central AI Service Facade (SRP, OCP, LSP)
    """
    def __init__(self):
        self._gate_enabled = True
        self.operations = {
            "prompt_manager": PromptManagerOperation(),
            "document_vision": DocumentVisionOperation(),
            "cash_flow_forecast": CashFlowForecastOperation(),
            "anomaly_detection": AnomalyDetectionOperation(),
            "trend_analysis": TrendAnalysisOperation(),
            "financial_insights": FinancialInsightsOperation(),
        }

    def _check_gate(self, payload: Dict = None, operation_type: str = AIOperationType.FINANCIAL_EXECUTION) -> bool:
        if not self._gate_enabled:
            return True
        return _check_hard_rules_gate(payload, operation_type)

    def prompt_manager_ai(self, admin_input: str) -> Dict[str, Any]:
        allowed = self._check_gate(payload=None, operation_type=AIOperationType.PROMPT_MANAGEMENT)
        if not allowed:
            return {"success": False, "blocked": True, "reason": "RULE_VIOLATION"}
        return self.operations["prompt_manager"].execute(admin_input)

    def process_document_with_vision(self, image_url: str, document_type: str = "invoice") -> Dict[str, Any]:
        if not self._check_gate(payload={"image_url": image_url}, operation_type=AIOperationType.FINANCIAL_EXECUTION):
            return {"success": False, "blocked": True, "reason": "RULE_VIOLATION"}
        return self.operations["document_vision"].execute(image_url, document_type)

    def generate_cash_flow_forecast(self, historical_data: List[Dict], periods: int = 6) -> List[Dict]:
        if not self._check_gate(payload={"historical_data": historical_data}, operation_type=AIOperationType.FINANCIAL_EXECUTION):
            return []
        return self.operations["cash_flow_forecast"].execute(historical_data, periods)

    def detect_anomalies(self, transactions: List[Dict]) -> List[Dict]:
        if not self._check_gate(payload={"transactions": transactions}, operation_type=AIOperationType.FINANCIAL_EXECUTION):
            return []
        return self.operations["anomaly_detection"].execute(transactions)

    def analyze_trends(self, financial_data: List[Dict], metrics: List[str] = None) -> List[Dict]:
        if metrics is None:
            metrics = ["revenue", "expenses", "profit"]
        if not self._check_gate(payload={"financial_data": financial_data}, operation_type=AIOperationType.FINANCIAL_EXECUTION):
            return []
        return self.operations["trend_analysis"].execute(financial_data, metrics)

    def generate_financial_insights(self, organization_data: Dict) -> List[str]:
        if not self._check_gate(payload={"organization_data": organization_data}, operation_type=AIOperationType.FINANCIAL_EXECUTION):
            return []
        return self.operations["financial_insights"].execute(organization_data)


# ======================================================
# Singleton Instance
# ======================================================

ai_service = AIService()
