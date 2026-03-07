from .base import ExplanationProvider

class StaticExplanationProvider(ExplanationProvider):
    def explain(self, context):
        issue_type = context.get("issue_type")
        explanations = {
            "MISSING_DOCUMENT": "المستند غير مكتمل حسب متطلبات النظام.",
            "RULE_VIOLATION": "العملية خالفت إحدى القواعد المحاسبية المعتمدة.",
            "DATA_MISMATCH": "يوجد عدم تطابق بين البيانات المدخلة."
        }
        return {
            "success": True,
            "explanation": explanations.get(
                issue_type,
                "لا يوجد شرح متاح لهذه الحالة."
            ),
            "source": "RULE_BASED_ENGINE"
        }
