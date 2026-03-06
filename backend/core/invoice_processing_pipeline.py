"""
Invoice Processing Pipeline Orchestrator - Master Service
منظم خط معالجة الفواتير - الخدمة الرئيسية

Orchestrates the complete 5-phase invoice processing pipeline:
1. Extraction: OpenAI Vision API extraction
2. Normalization: Data normalization and validation
3. Compliance: Compliance checks and audit findings
4. Cross-Document: Duplicate detection, anomalies, vendor risk
5. Financial Intelligence: Cash flow forecasting, spend intelligence, narratives
"""

import logging
from typing import Dict, List, Tuple, Any, Optional
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

# Import all phase services
from .openai_invoice_extraction_service import get_openai_extraction_service
from .dual_extraction_service import get_dual_extraction_service
from .data_normalization_service import DataNormalizationValidator
from .compliance_findings_service import ComplianceCheckService
from .cross_document_service import (
    DuplicateDetectionService,
    AnomalyDetectionService,
    VendorRiskService,
)
from .financial_intelligence_service import (
    CashFlowForecastService,
    SpendIntelligenceService,
    FinancialNarrativeService,
)


class InvoiceProcessingPipeline:
    """Master orchestrator for invoice processing through all 5 phases"""
    
    @staticmethod
    def process_invoice_complete(file_path: str,
                                 historical_invoices: List[Dict[str, Any]] = None,
                                 organization_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process complete invoice through all 5 phases
        
        Args:
            file_path: Path to invoice document (PDF, image, etc.)
            historical_invoices: List of historical invoice data for cross-document analysis
            organization_id: Organization context
        
        Returns:
            Dictionary containing results from all 5 phases
        """
        
        result = {
            'status': 'processing',
            'file_path': file_path,
            'organization_id': organization_id,
            'phases': {},
            'error': None,
        }
        
        try:
            # Phase 1: Extraction
            logger.info(f"Phase 1: Extracting invoice from {file_path}")
            phase1_result = InvoiceProcessingPipeline._phase1_extract(file_path)
            result['phases']['phase_1_extraction'] = phase1_result
            
            if not phase1_result.get('success'):
                result['status'] = 'failed'
                result['error'] = phase1_result.get('error')
                return result
            
            extracted_data = phase1_result.get('extracted_data', {})
            
            # Phase 2: Normalization & Validation
            logger.info("Phase 2: Normalizing and validating extracted data")
            phase2_result = InvoiceProcessingPipeline._phase2_normalize_validate(
                extracted_data
            )
            result['phases']['phase_2_normalization'] = phase2_result
            
            if not phase2_result.get('is_valid'):
                logger.warning(f"Validation failed: {phase2_result.get('validation_errors')}")
            
            normalized_data = phase2_result.get('normalized_data', extracted_data)
            
            # Phase 3: Compliance Checks & Findings
            logger.info("Phase 3: Performing compliance checks")
            phase3_result = InvoiceProcessingPipeline._phase3_compliance(normalized_data)
            result['phases']['phase_3_compliance'] = phase3_result
            
            # Phase 4: Cross-Document Intelligence
            logger.info("Phase 4: Analyzing cross-document patterns")
            phase4_result = InvoiceProcessingPipeline._phase4_cross_document(
                normalized_data,
                historical_invoices or []
            )
            result['phases']['phase_4_cross_document'] = phase4_result
            
            # Phase 5: Financial Intelligence
            logger.info("Phase 5: Generating financial intelligence")
            phase5_result = InvoiceProcessingPipeline._phase5_financial_intelligence(
                normalized_data,
                historical_invoices or [],
                phase3_result,
            )
            result['phases']['phase_5_financial'] = phase5_result
            
            # Overall status
            result['status'] = 'completed'
            result['overall_risk_score'] = InvoiceProcessingPipeline._calculate_overall_risk(
                phase3_result, phase4_result
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    @staticmethod
    def _phase1_extract(file_path: str) -> Dict[str, Any]:
        """Phase 1: Extract invoice data using OpenAI Vision + Tesseract Fallback"""
        try:
            # Use dual extraction service (OpenAI primary, Tesseract fallback)
            service = get_dual_extraction_service()
            extracted_data = service.extract_invoice_with_fallback_chain(file_path)
            
            return {
                'success': extracted_data.get('extraction_success', False),
                'extracted_data': extracted_data,
                'extraction_method': extracted_data.get('extraction_method', 'unknown'),
            }
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return {
                'success': False,
                'error': f"Extraction failed: {str(e)}",
            }
    
    @staticmethod
    def _phase2_normalize_validate(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 2: Normalize data and validate"""
        try:
            # Normalize
            normalized_data = DataNormalizationValidator.normalize_invoice_data(extracted_data)
            
            # Validate
            is_valid, errors, warnings = DataNormalizationValidator.validate_invoice_data(
                normalized_data
            )
            
            return {
                'normalized_data': normalized_data,
                'is_valid': is_valid,
                'validation_errors': errors,
                'validation_warnings': warnings,
                'error_count': len(errors),
                'warning_count': len(warnings),
            }
        except Exception as e:
            logger.error(f"Normalization failed: {str(e)}")
            return {
                'normalized_data': extracted_data,
                'is_valid': False,
                'validation_errors': [str(e)],
                'validation_warnings': [],
                'error_count': 1,
                'warning_count': 0,
            }
    
    @staticmethod
    def _phase3_compliance(normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: Perform compliance checks and generate findings"""
        try:
            # Perform checks
            checks = ComplianceCheckService.perform_compliance_checks(normalized_data)
            
            # Calculate risk score
            risk_score = ComplianceCheckService.calculate_overall_risk_score(checks)
            
            # Generate findings
            findings = ComplianceCheckService.generate_audit_findings(
                normalized_data, checks, risk_score
            )
            
            return {
                'status': 'completed',
                'compliance_checks': checks,
                'risk_score': risk_score,
                'risk_level': findings.get('risk_level'),
                'executive_summary': findings.get('executive_summary'),
                'key_findings': findings.get('key_findings'),
                'recommended_actions': findings.get('recommended_actions'),
                'audit_status': findings.get('audit_status'),
            }
        except Exception as e:
            logger.error(f"Compliance check failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'risk_score': 0,
            }
    
    @staticmethod
    def _phase4_cross_document(normalized_data: Dict[str, Any],
                              historical_invoices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Phase 4: Analyze cross-document patterns"""
        try:
            result = {
                'status': 'completed',
                'duplicate_detection': None,
                'anomaly_detection': None,
                'vendor_risk': None,
                'cross_document_risk_score': 0,
            }
            
            # Duplicate detection
            duplicates = DuplicateDetectionService.detect_duplicates(
                normalized_data, historical_invoices
            )
            result['duplicate_detection'] = duplicates
            
            # Anomaly detection
            vendor_history = [
                inv for inv in historical_invoices
                if inv.get('vendor_name') == normalized_data.get('vendor_name')
            ]
            
            anomalies = AnomalyDetectionService.detect_anomalies(
                normalized_data, vendor_history
            )
            result['anomaly_detection'] = anomalies
            
            # Vendor risk assessment
            vendor_risk = VendorRiskService.calculate_vendor_risk(
                normalized_data.get('vendor_name', 'Unknown'),
                vendor_history
            )
            result['vendor_risk'] = vendor_risk
            
            # Combine risk scores
            cross_doc_risk = (
                (duplicates.get('duplicate_risk_score', 0) * 0.35) +
                (anomalies.get('anomaly_risk_score', 0) * 0.35) +
                (vendor_risk.get('vendor_risk_score', 0) * 0.30)
            )
            result['cross_document_risk_score'] = int(cross_doc_risk)
            
            return result
        except Exception as e:
            logger.error(f"Cross-document analysis failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'cross_document_risk_score': 0,
            }
    
    @staticmethod
    def _phase5_financial_intelligence(normalized_data: Dict[str, Any],
                                      historical_invoices: List[Dict[str, Any]],
                                      compliance_findings: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: Generate financial intelligence"""
        try:
            result = {
                'status': 'completed',
                'cash_flow_forecast': None,
                'spend_intelligence': None,
                'financial_narrative': None,
            }
            
            # Include current invoice in history for analysis
            analysis_history = [normalized_data] + historical_invoices
            
            # Cash flow forecasting
            cash_flow = CashFlowForecastService.forecast_cash_flow(
                analysis_history, forecast_period_days=90
            )
            result['cash_flow_forecast'] = cash_flow
            
            # Spend intelligence
            spend = SpendIntelligenceService.analyze_spend_intelligence(
                analysis_history, time_period_months=12
            )
            result['spend_intelligence'] = spend
            
            # Financial narratives
            invoice_narrative = FinancialNarrativeService.generate_financial_narrative(
                normalized_data, spend, compliance_findings
            )
            result['financial_narrative'] = invoice_narrative
            
            spend_narrative = FinancialNarrativeService.generate_spend_narrative(spend)
            result['spend_narrative'] = spend_narrative
            
            return result
        except Exception as e:
            logger.error(f"Financial intelligence failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
            }
    
    @staticmethod
    def _calculate_overall_risk(compliance_result: Dict[str, Any],
                               cross_doc_result: Dict[str, Any]) -> int:
        """Calculate overall risk score from compliance and cross-document"""
        compliance_score = compliance_result.get('risk_score', 0)
        cross_doc_score = cross_doc_result.get('cross_document_risk_score', 0)
        
        # Weighted average: compliance 60%, cross-document 40%
        overall = (compliance_score * 0.6) + (cross_doc_score * 0.4)
        
        return int(min(100, overall))


class ProcessingPipelineManager:
    """Manager for orchestrating pipeline with database integration"""
    
    @staticmethod
    def process_and_store(file_path: str,
                        document_id: Optional[str] = None,
                        organization_id: Optional[str] = None,
                        historical_invoices: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process invoice and prepare for database storage
        
        Args:
            file_path: Path to invoice document
            document_id: Associated Document model ID
            organization_id: Organization context
            historical_invoices: Historical data for comparison
        
        Returns:
            Processing result ready for ExtractedData model
        """
        
        result = InvoiceProcessingPipeline.process_invoice_complete(
            file_path, historical_invoices, organization_id
        )
        
        if result['status'] != 'completed':
            return {
                'status': result['status'],
                'error': result.get('error'),
            }
        
        # Extract data for database storage
        phase_results = result.get('phases', {})
        
        extracted_fields = {
            # Phase 1 fields
            'extracted_data': phase_results.get('phase_1_extraction', {}).get('extracted_data', {}),
            'extraction_status': 'completed',
            'confidence': phase_results.get('phase_1_extraction', {}).get('extracted_data', {}).get('confidence', 0),
            
            # Phase 2 fields
            'normalized_json': json.dumps(
                phase_results.get('phase_2_normalization', {}).get('normalized_data', {})
            ),
            'validation_errors': phase_results.get('phase_2_normalization', {}).get('validation_errors', []),
            'validation_warnings': phase_results.get('phase_2_normalization', {}).get('validation_warnings', []),
            'is_valid': phase_results.get('phase_2_normalization', {}).get('is_valid', False),
            
            # Phase 3 fields
            'compliance_checks': json.dumps(
                phase_results.get('phase_3_compliance', {}).get('compliance_checks', {})
            ),
            'risk_score': phase_results.get('phase_3_compliance', {}).get('risk_score', 0),
            'risk_level': phase_results.get('phase_3_compliance', {}).get('risk_level', 'unknown'),
            'audit_summary': phase_results.get('phase_3_compliance', {}).get('executive_summary', ''),
            
            # Phase 4 fields
            'duplicate_score': phase_results.get('phase_4_cross_document', {}).get('duplicate_detection', {}).get('duplicate_risk_score', 0),
            'anomaly_flags': json.dumps(
                phase_results.get('phase_4_cross_document', {}).get('anomaly_detection', {}).get('anomaly_flags', [])
            ),
            'vendor_risk_score': phase_results.get('phase_4_cross_document', {}).get('vendor_risk', {}).get('vendor_risk_score', 0),
            
            # Phase 5 fields (references/summaries)
            'financial_narrative': phase_results.get('phase_5_financial', {}).get('financial_narrative', {}).get('executive_summary', ''),
        }
        
        return {
            'status': 'success',
            'document_id': document_id,
            'organization_id': organization_id,
            'extracted_fields': extracted_fields,
            'processing_result': result,
        }


def get_invoice_pipeline() -> InvoiceProcessingPipeline:
    """Get invoice processing pipeline"""
    return InvoiceProcessingPipeline()


def get_pipeline_manager() -> ProcessingPipelineManager:
    """Get pipeline manager"""
    return ProcessingPipelineManager()
