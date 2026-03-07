"""
Dual Extraction Service - OpenAI + Tesseract Support
خدمة الاستخراج الثنائية - دعم OpenAI و Tesseract

This service provides intelligent fallback between:
1. OpenAI Vision API (primary, high accuracy)
2. Tesseract OCR (secondary, as backup if available)

Configuration via .env:
- EXTRACTION_PRIMARY_METHOD: openai or tesseract
- TESSERACT_ENABLED: Enable Tesseract fallback (True/False)
- TESSERACT_CMD: Tesseract command path
"""

import os
import json
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any
import re

from django.conf import settings

logger = logging.getLogger(__name__)


class DualExtractionService:
    """
    Service supporting both OpenAI Vision and Tesseract OCR extraction.
    Tries primary method first, falls back to secondary if unavailable.
    """
    
    def __init__(self):
        """Initialize extraction service with configuration"""
        self.primary_method = os.getenv('EXTRACTION_PRIMARY_METHOD', 'openai').lower()
        self.tesseract_enabled = os.getenv('TESSERACT_ENABLED', 'True').lower() == 'true'
        self.tesseract_cmd = os.getenv('TESSERACT_CMD', 'tesseract')
        self.confidence_threshold = int(os.getenv('TESSERACT_CONFIDENCE_THRESHOLD', '60'))
        
        # Initialize both services
        self.openai_service = None
        self.tesseract_service = None
        
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize available extraction services"""
        # Always try to initialize OpenAI
        try:
            from core.openai_invoice_extraction_service import get_openai_extraction_service
            self.openai_service = get_openai_extraction_service()
            logger.info("✓ OpenAI extraction service initialized")
        except Exception as e:
            logger.warning(f"Could not initialize OpenAI service: {e}")
        
        # Try to initialize Tesseract if enabled
        if self.tesseract_enabled:
            if self._check_tesseract_available():
                try:
                    from core.tesseract_extraction_service import get_tesseract_extraction_service
                    self.tesseract_service = get_tesseract_extraction_service()
                    logger.info("✓ Tesseract extraction service initialized")
                except Exception as e:
                    logger.warning(f"Could not initialize Tesseract service: {e}")
            else:
                logger.warning("Tesseract not available on system (install: apt-get install tesseract-ocr)")
    
    def _check_tesseract_available(self) -> bool:
        """Check if Tesseract binary is available"""
        import shutil
        return shutil.which(self.tesseract_cmd) is not None
    
    def extract_invoice(self, file_path: str) -> Dict[str, Any]:
        """
        Extract invoice using configured strategy
        
        Args:
            file_path: Path to invoice document
        
        Returns:
            Dictionary with extracted invoice data
        """
        result = None
        extraction_method = None
        
        # Try primary method first
        if self.primary_method == 'openai' and self.openai_service:
            logger.info(f"Attempting OpenAI extraction for {file_path}")
            try:
                result = self.openai_service.extract_invoice(file_path)
                if result and result.get('extraction_success', False):
                    extraction_method = 'openai_vision'
                    logger.info(f"✓ OpenAI extraction successful")
            except Exception as e:
                logger.warning(f"OpenAI extraction failed: {e}")
        
        # Fallback to Tesseract if primary failed and enabled
        if not result or not result.get('extraction_success'):
            if self.tesseract_enabled and self.tesseract_service:
                logger.info(f"Falling back to Tesseract extraction for {file_path}")
                try:
                    result = self.tesseract_service.extract_invoice(file_path)
                    if result and result.get('extraction_success', False):
                        extraction_method = 'tesseract_ocr'
                        logger.info(f"✓ Tesseract extraction successful")
                except Exception as e:
                    logger.warning(f"Tesseract extraction failed: {e}")
        
        # If both failed, return error
        if not result or not result.get('extraction_success'):
            logger.error("All extraction methods failed")
            return self._error_extraction(extraction_method or 'unknown')
        
        # Add extraction method metadata + is_fallback flag (SOLID: callers depend on this contract)
        result['extraction_method'] = extraction_method
        result['dual_service_enabled'] = True
        # is_fallback = True whenever the secondary (Tesseract) provider was used instead of OpenAI
        result['is_fallback'] = extraction_method == 'tesseract_ocr'

        return result
    
    def extract_invoice_with_fallback_chain(self, file_path: str) -> Dict[str, Any]:
        """
        Try all available extraction methods in order of preference
        
        Args:
            file_path: Path to invoice document
        
        Returns:
            Dictionary with extracted invoice data and method used
        """
        methods_attempted = []
        
        # Determine extraction order based on config
        if self.primary_method == 'openai':
            extraction_order = ['openai', 'tesseract']
        else:
            extraction_order = ['tesseract', 'openai']
        
        for method in extraction_order:
            if method == 'openai' and self.openai_service:
                logger.info(f"[Chain] Attempting OpenAI extraction")
                methods_attempted.append('openai')
                try:
                    result = self.openai_service.extract_invoice(file_path)
                    if result and result.get('extraction_success', False):
                        result['extraction_method'] = 'openai_vision'
                        result['methods_attempted'] = methods_attempted
                        result['is_fallback'] = False
                        logger.info(f"[Chain] ✓ OpenAI succeeded after {len(methods_attempted)} attempt(s)")
                        return result
                except Exception as e:
                    logger.warning(f"[Chain] OpenAI failed: {e}")
            
            elif method == 'tesseract' and self.tesseract_enabled and self.tesseract_service:
                logger.info(f"[Chain] Attempting Tesseract extraction")
                methods_attempted.append('tesseract')
                try:
                    result = self.tesseract_service.extract_invoice(file_path)
                    if result and result.get('extraction_success', False):
                        result['extraction_method'] = 'tesseract_ocr'
                        result['methods_attempted'] = methods_attempted
                        result['is_fallback'] = True  # Tesseract = fallback provider
                        logger.info(f"[Chain] ✓ Tesseract succeeded after {len(methods_attempted)} attempt(s)")
                        return result
                except Exception as e:
                    logger.warning(f"[Chain] Tesseract failed: {e}")
        
        # All methods failed
        logger.error(f"All extraction methods failed. Attempted: {methods_attempted}")
        result = self._error_extraction('all_failed')
        result['methods_attempted'] = methods_attempted
        return result
    
    def _error_extraction(self, failed_method: str) -> Dict[str, Any]:
        """Return error extraction result"""
        return {
            "extraction_success": False,
            "extraction_engine": failed_method,
            "extraction_timestamp": datetime.now().isoformat(),
            "invoice_number": None,
            "issue_date": None,
            "due_date": None,
            "vendor_name": None,
            "customer_name": None,
            "total_amount": None,
            "currency": "SAR",
            "items": [],
            "language_detected": "unknown",
            "confidence": 0,
            "error": f"All extraction methods unavailable. Last attempt: {failed_method}"
        }
    
    def get_extraction_status(self) -> Dict[str, Any]:
        """Get status of all extraction services"""
        return {
            'primary_method': self.primary_method,
            'openai_available': self.openai_service is not None,
            'tesseract_enabled': self.tesseract_enabled,
            'tesseract_available': self.tesseract_service is not None and self._check_tesseract_available(),
            'tesseract_cmd': self.tesseract_cmd,
            'confidence_threshold': self.confidence_threshold,
            'timestamp': datetime.now().isoformat(),
        }


# Singleton instance
_dual_service = None


def get_dual_extraction_service() -> DualExtractionService:
    """Get or create singleton instance of dual extraction service"""
    global _dual_service
    if _dual_service is None:
        _dual_service = DualExtractionService()
    return _dual_service
