"""
FinAI Core AI Module - Advanced AI Intelligence Platform

Comprehensive AI services for:
- Document Understanding (entity extraction, semantic analysis, classification)
- Forecasting Intelligence (trend explanation, prediction commentary)
- Anomaly Detection (suspicious pattern analysis, risk scoring)
- ZATCA Compliance (validation interpretation, violation detection)
- Extended Explanations (audit reports, finding analysis)
- AI Orchestration (unified service coordination)

Plus original capabilities:
- Document OCR (vision model + Tesseract fallback)
- Structured data extraction (invoices, accounting entries)
- Compliance explanations (Arabic-focused)

All operations are:
- Secure: No SSRF, organization-isolated, file-read based
- Observable: Comprehensive logging with redaction
- Reliable: Retry logic, fallbacks, timeouts
- Compliant: Audit trails, confidence scoring
- Scalable: Service-layer architecture, horizontal scaling ready
"""

# Core infrastructure
from .client import OpenAIClient, get_openai_client
from .errors import AIServiceError, AIAPIError, FileProcessingError, RateLimitError, TimeoutError, ValidationError

# Original AI modules
from .ocr import OCRProcessor
from .extract import StructuredExtractor
from .explain import ComplianceExplainer

# Advanced AI modules
from .document_understanding import DocumentUnderstanding
from .forecasting_ai import ForecastingAI
from .anomaly_detection_ai import AnomalyDetectionAI
from .compliance_ai import ZATCAComplianceAI
from .explanation_ai import ExtendedExplanationAI

# Orchestration and coordination
from .ai_orchestrator import AIOrchestrator, get_ai_orchestrator

__all__ = [
    # Infrastructure
    'OpenAIClient',
    'get_openai_client',
    'AIServiceError',
    'AIAPIError',
    'FileProcessingError',
    'RateLimitError',
    'TimeoutError',
    'ValidationError',
    
    # Original modules
    'OCRProcessor',
    'StructuredExtractor',
    'ComplianceExplainer',
    
    # Advanced modules
    'DocumentUnderstanding',
    'ForecastingAI',
    'AnomalyDetectionAI',
    'ZATCAComplianceAI',
    'ExtendedExplanationAI',
    
    # Orchestration
    'AIOrchestrator',
    'get_ai_orchestrator',
]
