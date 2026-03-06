from .models import AIPluginSetting
from .models import AIPluginSetting
from django.db import OperationalError, ProgrammingError
from types import SimpleNamespace
class AIPluginSettingsService:

    @staticmethod
    def get(plugin_code: str):
        try:
            setting = AIPluginSetting.objects.get(
                plugin_code=plugin_code,
                is_enabled=True
            )
            return setting
        except (AIPluginSetting.DoesNotExist, OperationalError, ProgrammingError):
            # Fallback: return default classical engine config
            import os
            ocr_config = {"provider": "Tesseract", "model_name": "Document Reader", "label": "OCR"}
            if plugin_code == "ocr":
                if os.name == "nt":
                    # Windows: use pytesseract
                    ocr_config["python_module"] = "pytesseract"
                    ocr_config["tesseract_path"] = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
                else:
                    ocr_config["python_module"] = "tesseract"
            fallback = {
                "pattern":      {"provider": "scikit-learn", "model_name": "Pattern Engine", "label": "كشف نمط"},
                "text_summary": {"provider": "Gensim",       "model_name": "Text Normalizer", "label": "تلخيص نص"},
                "anomaly":      {"provider": "PyOD",         "model_name": "Risk Signal",     "label": "شذوذ"},
                "ocr":          ocr_config,
                "rules":        {"provider": "Rules Engine",  "model_name": "Compliance Validator", "label": "قواعد"},
            }
            data = fallback.get(plugin_code, None)
            return SimpleNamespace(**data) if data else None
