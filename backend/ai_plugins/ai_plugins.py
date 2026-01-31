# Module: ai_plugins
# إدارة مكتبات الذكاء الاصطناعي المدعومة في النظام

AI_LIBRARIES = [
    {
        "name": "OpenAI",
        "provider": "openai",
        "description": "OpenAI API for LLMs and AI services.",
        "supported": True
    },
    {
        "name": "Google Cloud AI",
        "provider": "google_cloud",
        "description": "Google Cloud AI and Vertex AI APIs.",
        "supported": True
    },
    {
        "name": "Azure Cognitive Services",
        "provider": "azure",
        "description": "Microsoft Azure AI and Cognitive Services.",
        "supported": True
    },
    {
        "name": "Local Model",
        "provider": "local",
        "description": "Self-hosted or on-premise AI models.",
        "supported": True
    },
    # Classical AI libraries for fallback/default
    {
        "name": "Pattern Engine",
        "provider": "scikit-learn",
        "description": "كشف نمط باستخدام scikit-learn.",
        "supported": True
    },
    {
        "name": "Text Normalizer",
        "provider": "Gensim",
        "description": "تلخيص نص باستخدام Gensim.",
        "supported": True
    },
    {
        "name": "Risk Signal",
        "provider": "PyOD",
        "description": "كشف الشذوذ باستخدام PyOD.",
        "supported": True
    },
    {
        "name": "Document Reader",
        "provider": "Tesseract",
        "description": "OCR باستخدام Tesseract أو pytesseract.",
        "supported": True
    },
    {
        "name": "Compliance Validator",
        "provider": "Rules Engine",
        "description": "التحقق من القواعد باستخدام Rules Engine.",
        "supported": True
    }
]

# دالة لإرجاع قائمة المكتبات المدعومة

def get_supported_ai_libraries():
    return AI_LIBRARIES
