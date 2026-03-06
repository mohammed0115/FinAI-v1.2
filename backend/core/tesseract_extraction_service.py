"""
Tesseract OCR Invoice Extraction Service - Phase 1 Fallback
خدمة استخراج الفواتير من Tesseract

This service uses Tesseract OCR to extract invoice data as a fallback when OpenAI is unavailable.

Features:
- OCR-based invoice extraction
- Support for Arabic and English text
- Automatic language detection
- Structured JSON output from OCR text
- Works with images and PDFs
"""

import os
import json
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any
import re
from collections import defaultdict

from django.conf import settings

try:
    import pytesseract
    from PIL import Image
    import pdf2image
except ImportError:
    pytesseract = None
    Image = None
    pdf2image = None

logger = logging.getLogger(__name__)


class TesseractInvoiceExtractionService:
    """
    Service for extracting structured invoice data using Tesseract OCR
    """
    
    def __init__(self):
        """Initialize Tesseract service"""
        self.tesseract_cmd = os.getenv('TESSERACT_CMD', 'tesseract')
        self.confidence_threshold = int(os.getenv('TESSERACT_CONFIDENCE_THRESHOLD', '60'))
        self.available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if Tesseract is available"""
        if pytesseract is None:
            logger.warning("pytesseract not installed")
            return False
        
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"✓ Tesseract available: {version}")
            return True
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract binary not found in PATH")
            return False
        except Exception as e:
            logger.warning(f"Tesseract check failed: {e}")
            return False
    
    def extract_invoice(self, file_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from document using Tesseract OCR
        
        Args:
            file_path: Path to document file (image or PDF)
        
        Returns:
            Dictionary with extracted invoice data
        """
        if not self.available:
            logger.warning("Tesseract not available")
            return {
                'extraction_success': False,
                'error': 'Tesseract not available',
                'extraction_engine': 'tesseract_fallback'
            }
        
        try:
            # Read image
            if file_path.lower().endswith('.pdf'):
                images = self._pdf_to_images(file_path)
                if not images:
                    return self._error_result("Could not convert PDF to images")
                image = images[0]  # Use first page
            else:
                image = Image.open(file_path)
            
            # Extract text using Tesseract
            ocr_text = pytesseract.image_to_string(
                image,
                lang='ara+eng'  # Arabic and English
            )
            
            if not ocr_text or ocr_text.strip() == '':
                logger.warning("No text extracted from image")
                return self._error_result("No text extracted from image")
            
            # Parse extracted text into structured invoice
            invoice_data = self._parse_invoice_text(ocr_text)
            
            if not invoice_data:
                return self._error_result("Could not parse invoice from OCR text")
            
            # Add metadata
            invoice_data['extraction_success'] = True
            invoice_data['extraction_engine'] = 'tesseract_ocr'
            invoice_data['extraction_timestamp'] = datetime.now().isoformat()
            invoice_data['confidence'] = 65  # Typical OCR confidence
            invoice_data['language_detected'] = self._detect_language(ocr_text)
            invoice_data['ocr_raw_text'] = ocr_text[:500]  # Store first 500 chars for audit
            
            logger.info(f"✓ Tesseract extraction successful: {invoice_data.get('invoice_number', 'N/A')}")
            return invoice_data
            
        except Exception as e:
            logger.error(f"Tesseract extraction error: {e}", exc_info=True)
            return self._error_result(str(e))
    
    def _pdf_to_images(self, pdf_path: str) -> List:
        """Convert PDF to images"""
        try:
            if pdf2image is None:
                logger.warning("pdf2image not installed")
                return []
            
            images = pdf2image.convert_from_path(pdf_path, first_page=1, last_page=1)
            return images
        except Exception as e:
            logger.error(f"PDF conversion error: {e}")
            return []
    
    def _parse_invoice_text(self, ocr_text: str) -> Dict[str, Any]:
        """
        Parse OCR text into structured invoice data
        
        Args:
            ocr_text: Raw text from OCR
        
        Returns:
            Dictionary with parsed invoice fields
        """
        data = {
            'invoice_number': None,
            'issue_date': None,
            'due_date': None,
            'vendor_name': None,
            'customer_name': None,
            'total_amount': None,
            'tax_amount': None,
            'tax_rate': None,
            'subtotal': None,
            'discount_amount': None,
            'currency': 'SAR',
            'items': [],
            'vendor_tax_id': None,
            'customer_tax_id': None,
        }
        
        lines = ocr_text.split('\n')
        
        # Extract invoice number (look for patterns like INV-, Invoice #, etc.)
        for line in lines:
            if re.search(r'(inv|invoice|رقم فاتورة|فاتورة)\s*[#:]\s*([A-Z0-9\-]+)', line, re.IGNORECASE | re.UNICODE):
                match = re.search(r'([A-Z0-9\-]+)', line.split(':')[-1] if ':' in line else line)
                if match:
                    data['invoice_number'] = match.group(1)
                    break
        
        # Extract dates
        date_patterns = [
            r'(\d{4}[-/]\d{2}[-/]\d{2})',  # YYYY-MM-DD
            r'(\d{2}[-/]\d{2}[-/]\d{4})',  # DD-MM-YYYY
        ]
        
        date_found = False
        for line in lines:
            for pattern in date_patterns:
                matches = re.findall(pattern, line)
                if matches:
                    if not date_found:
                        data['issue_date'] = self._normalize_date(matches[0])
                        date_found = True
                    elif len(matches) > 1:
                        data['due_date'] = self._normalize_date(matches[1])
        
        # Extract amounts (look for large numbers, typically formatted)
        amount_patterns = [
            r'(?:total|إجمالي|المجموع)\s*[:\-]?\s*([\d,]+\.?\d*)',
            r'([\d,]+\.?\d{2})\s*(?:sar|aed|usd|ريال|درهم)',
        ]
        
        amount_matches = []
        for pattern in amount_patterns:
            matches = re.findall(pattern, ocr_text, re.IGNORECASE | re.UNICODE)
            amount_matches.extend(matches)
        
        if amount_matches:
            # Get the largest amount as total
            try:
                amounts = []
                for amt in amount_matches:
                    cleaned = amt.replace(',', '').replace(' ', '')
                    amounts.append(Decimal(cleaned))
                if amounts:
                    data['total_amount'] = max(amounts)
            except:
                pass
        
        # Extract vendor name (usually near top or after "From:" / "من:")
        vendor_candidates = []
        for i, line in enumerate(lines[:20]):  # Check first 20 lines
            if line.strip() and len(line.strip()) > 5 and len(line.strip()) < 100:
                if not any(x in line.lower() for x in ['invoice', 'date', 'amount', 'total']):
                    vendor_candidates.append(line.strip())
        
        if vendor_candidates:
            data['vendor_name'] = vendor_candidates[0]
        
        # Extract tax IDs
        vat_pattern = r'(?:vat|tax|ضريبة|ض\.ب)\s*[#:]\s*([A-Z0-9\-]+)'
        vat_matches = re.findall(vat_pattern, ocr_text, re.IGNORECASE | re.UNICODE)
        if vat_matches:
            data['vendor_tax_id'] = vat_matches[0]
        
        # Extract line items (simplified - look for quantity x price patterns)
        item_pattern = r'(\d+)\s*(?:x|×|\*)\s*([\d,]+\.?\d*)'
        items_matches = re.findall(item_pattern, ocr_text)
        for qty, price in items_matches[:10]:  # Limit to 10 items
            try:
                data['items'].append({
                    'quantity': int(qty),
                    'unit_price': Decimal(price.replace(',', '')),
                    'line_total': Decimal(qty) * Decimal(price.replace(',', '')),
                    'description': 'Item from OCR extraction'
                })
            except:
                pass
        
        return data
    
    def _normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date string to YYYY-MM-DD format"""
        try:
            from dateutil import parser
            parsed = parser.parse(date_str)
            return parsed.strftime('%Y-%m-%d')
        except:
            return None
    
    def _detect_language(self, text: str) -> str:
        """Detect language in text (Arabic, English, or mixed)"""
        arabic_count = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return 'unknown'
        
        arabic_ratio = arabic_count / total_chars
        
        if arabic_ratio > 0.7:
            return 'ar'
        elif arabic_ratio < 0.3:
            return 'en'
        else:
            return 'mixed'
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return error result"""
        return {
            'extraction_success': False,
            'extraction_engine': 'tesseract_ocr',
            'extraction_timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'confidence': 0,
        }


# Singleton instance
_tesseract_service = None


def get_tesseract_extraction_service() -> TesseractInvoiceExtractionService:
    """Get or create singleton instance of Tesseract extraction service"""
    global _tesseract_service
    if _tesseract_service is None:
        _tesseract_service = TesseractInvoiceExtractionService()
    return _tesseract_service
