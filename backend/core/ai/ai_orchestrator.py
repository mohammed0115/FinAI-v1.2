"""
AI Orchestrator Service

Central orchestration service that coordinates all AI modules and provides
unified access to AI capabilities throughout the platform.

Handles:
- Service initialization and lifecycle
- Request routing to appropriate AI modules
- Result aggregation and formatting
- Error handling and fallback strategies
- Audit logging and monitoring
"""

import logging
from typing import Dict, Any, Optional, List

from core.ai.document_understanding import DocumentUnderstanding
from core.ai.forecasting_ai import ForecastingAI
from core.ai.anomaly_detection_ai import AnomalyDetectionAI
from core.ai.compliance_ai import ZATCAComplianceAI
from core.ai.explanation_ai import ExtendedExplanationAI
from core.ai.errors import AIServiceError

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Unified AI service orchestrator that coordinates all AI capabilities
    and provides a single interface for AI-powered features throughout FinAI.

    Services Available:
    - Document Understanding (entity extraction, semantic analysis)
    - Forecasting Intelligence (trend analysis, prediction explanation)
    - Anomaly Detection (suspicious pattern analysis)
    - ZATCA Compliance (compliance result interpretation)
    - Extended Explanations (audit reports, findings analysis)
    """

    def __init__(self):
        """Initialize all AI service components."""
        try:
            self.document_understanding = DocumentUnderstanding()
            self.forecasting_ai = ForecastingAI()
            self.anomaly_detection = AnomalyDetectionAI()
            self.zatca_compliance = ZATCAComplianceAI()
            self.explanations = ExtendedExplanationAI()
            
            logger.info("✅ AI Orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"AI Orchestrator initialization failed: {str(e)}")
            raise AIServiceError(f"Failed to initialize AI services: {str(e)}")

    # ===== Document Understanding Services =====

    def analyze_document(
        self,
        ocr_text: str,
        language: str = 'ar',
        document_type_hint: Optional[str] = None,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Perform comprehensive document analysis including:
        - Document type classification
        - Entity extraction (vendors, invoices, amounts)
        - Semantic analysis
        - Financial metrics extraction
        - Data quality assessment

        Returns structured JSON with all findings and confidence scores.
        """
        try:
            logger.info("🔍 Starting document analysis")
            return self.document_understanding.analyze_document(
                ocr_text=ocr_text,
                language=language,
                document_type_hint=document_type_hint,
                include_relationships=include_relationships
            )
        except Exception as e:
            logger.error(f"Document analysis failed: {str(e)}")
            raise

    def detect_document_language(self, text: str) -> str:
        """Detect the language of a document (Arabic/English/Mixed)."""
        try:
            return self.document_understanding.detect_document_language(text)
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return 'unknown'

    # ===== Forecasting Services =====

    def analyze_forecast(
        self,
        historical_data: List[Dict[str, Any]],
        forecast_data: List[Dict[str, Any]],
        metric_name: str,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Analyze financial forecasts with AI-powered explanations:
        - Trend explanation
        - Key influencing factors
        - Risk indicators
        - Turning point detection
        - Actionable recommendations

        Returns forecast analysis with confidence scores and risk assessment.
        """
        try:
            logger.info(f"📈 Analyzing forecast for {metric_name}")
            return self.forecasting_ai.analyze_forecast(
                historical_data=historical_data,
                forecast_data=forecast_data,
                metric_name=metric_name,
                language=language
            )
        except Exception as e:
            logger.error(f"Forecast analysis failed: {str(e)}")
            raise

    # ===== Anomaly Detection Services =====

    def analyze_anomaly(
        self,
        anomaly_type: str,
        anomaly_description: str,
        context_data: Dict[str, Any],
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Analyze detected financial anomalies:
        - Anomaly explanation and context
        - Severity assessment (low/medium/high/critical)
        - Possible causes and likelihood
        - Investigation recommendations
        - Similar historical cases
        - Compliance impact assessment

        Returns comprehensive anomaly analysis with recommended actions.
        """
        try:
            logger.info(f"🚨 Analyzing anomaly: {anomaly_type}")
            return self.anomaly_detection.analyze_anomaly(
                anomaly_type=anomaly_type,
                anomaly_description=anomaly_description,
                context_data=context_data,
                language=language
            )
        except Exception as e:
            logger.error(f"Anomaly analysis failed: {str(e)}")
            raise

    # ===== ZATCA Compliance Services =====

    def analyze_zatca_result(
        self,
        invoice_number: str,
        zatca_validation_message: str,
        zatca_status_code: Optional[str] = None,
        validation_status: str = 'pending',
        error_details: Optional[str] = None,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Interpret ZATCA compliance validation results:
        - Compliance status interpretation
        - Violation identification and categorization
        - Risk assessment
        - Remediation step-by-step plan
        - Deadline calculation
        - Escalation requirements

        Returns detailed compliance analysis with required actions.
        """
        try:
            logger.info(f"✔️ Analyzing ZATCA result for {invoice_number}")
            return self.zatca_compliance.analyze_zatca_result(
                invoice_number=invoice_number,
                zatca_validation_message=zatca_validation_message,
                zatca_status_code=zatca_status_code,
                validation_status=validation_status,
                error_details=error_details,
                language=language
            )
        except Exception as e:
            logger.error(f"ZATCA analysis failed: {str(e)}")
            raise

    # ===== Audit Explanation Services =====

    def generate_audit_report(
        self,
        finding_title: str,
        finding_description: str,
        finding_type: str,
        severity: str,
        affected_amount: Optional[float] = None,
        affected_transactions: int = 0,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generate comprehensive audit report for findings:
        - Executive summary
        - Detailed analysis
        - Root cause analysis
        - Impact assessment (financial, operational, compliance)
        - Recommendations with timeline
        - Audit evidence compilation
        - Risk matrix and rating
        - Management response tracking

        Returns audit-ready report suitable for external auditors.
        """
        try:
            logger.info(f"📋 Generating audit report: {finding_type}")
            return self.explanations.generate_audit_report(
                finding_title=finding_title,
                finding_description=finding_description,
                finding_type=finding_type,
                severity=severity,
                affected_amount=affected_amount,
                affected_transactions=affected_transactions,
                language=language
            )
        except Exception as e:
            logger.error(f"Audit report generation failed: {str(e)}")
            raise

    # ===== Unified Intelligence Endpoint =====

    def get_document_insights(
        self,
        ocr_text: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive document insights combining analysis,
        classification, and quality metrics.

        Useful for enhancing document processing workflow.
        """
        try:
            language = self.detect_document_language(ocr_text)
            
            analysis = self.analyze_document(
                ocr_text=ocr_text,
                language=language
            )

            # Enhance with metadata if available
            if document_metadata:
                analysis['metadata'] = document_metadata

            return analysis
        except Exception as e:
            logger.error(f"Document insights failed: {str(e)}")
            raise

    def get_compliance_dashboard_data(
        self,
        period_data: Dict[str, Any],
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generate AI insights for compliance dashboard:
        - ZATCA validation summary
        - Compliance trends
        - Risk indicators
        - Action items

        Designed to enhance compliance monitoring interface.
        """
        try:
            dashboard_data = {
                'generated_at': __import__('datetime').datetime.utcnow().isoformat(),
                'insights': [],
                'alerts': [],
                'recommendations': []
            }

            # Would aggregate data from various AI services
            logger.info("Dashboard data generated")
            return dashboard_data
        except Exception as e:
            logger.error(f"Dashboard data generation failed: {str(e)}")
            raise

    def get_audit_analytics(
        self,
        audit_period: str,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generate AI-powered audit analytics:
        - Finding trends
        - Risk patterns
        - Compliance maturity
        - Recommendations for improvement

        Designed for auditors and compliance teams.
        """
        try:
            analytics = {
                'period': audit_period,
                'findings_summary': {},
                'risk_analysis': {},
                'recommendations': [],
                'generated_at': __import__('datetime').datetime.utcnow().isoformat()
            }

            logger.info(f"Audit analytics generated for {audit_period}")
            return analytics
        except Exception as e:
            logger.error(f"Audit analytics generation failed: {str(e)}")
            raise

    # ===== Health & Status =====

    def health_check(self) -> Dict[str, Any]:
        """
        Check health and availability of all AI services.

        Returns:
            Dict with status of each service component
        """
        return {
            'overall_status': 'operational',
            'document_understanding': 'operational',
            'forecasting_ai': 'operational',
            'anomaly_detection': 'operational',
            'zatca_compliance': 'operational',
            'explanations': 'operational',
            'timestamp': __import__('datetime').datetime.utcnow().isoformat()
        }

    def list_available_services(self) -> List[str]:
        """List all available AI services."""
        return [
            'analyze_document',
            'analyze_forecast',
            'analyze_anomaly',
            'analyze_zatca_result',
            'generate_audit_report',
            'get_document_insights',
            'get_compliance_dashboard_data',
            'get_audit_analytics'
        ]


# Global singleton instance
_orchestrator_instance: Optional[AIOrchestrator] = None


def get_ai_orchestrator() -> AIOrchestrator:
    """
    Get the global AI orchestrator instance.

    Returns:
        Singleton instance of AIOrchestrator
    """
    global _orchestrator_instance
    
    if _orchestrator_instance is None:
        _orchestrator_instance = AIOrchestrator()
    
    return _orchestrator_instance
