"""
Document OCR Service - خدمة التعرف الضوئي على الحروف

SCOPE: READ-ONLY EVIDENCE EXTRACTION
This service extracts text from uploaded documents using OCR.
Extracted text is stored as AUDIT EVIDENCE, not as source of truth.

Features:
- Printed text extraction
- Handwriting recognition (best-effort)
- Arabic-first OCR support
- Confidence scoring
- Full traceability

COMPLIANCE:
- OCR output is evidence, not accounting truth
- Original documents are preserved
- All extractions are timestamped
- No editing of extracted text
"""
import os
import io
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import tempfile
import re

from django.conf import settings
from django.utils import timezone

import pytesseract
from PIL import Image
from pdf2image import convert_from_path, convert_from_bytes

logger = logging.getLogger(__name__)

# OCR Configuration
TESSERACT_LANG_ARABIC = 'ara'
TESSERACT_LANG_ENGLISH = 'eng'
TESSERACT_LANG_MIXED = 'ara+eng'

# Supported file types
SUPPORTED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.gif']
SUPPORTED_PDF_TYPE = '.pdf'


class OCRConfidence:
    """OCR Confidence levels"""
    HIGH = 80
    MEDIUM = 60
    LOW = 40


class DocumentOCRService:
    """
    خدمة التعرف الضوئي على المستندات
    Document OCR Processing Service
    
    READ-ONLY: Extracts text from documents as audit evidence.
    Does NOT modify or edit extracted content.
    """
    
    def __init__(self):
        self._verify_tesseract()
    
    def _verify_tesseract(self):
        """Verify tesseract is installed and available"""
        try:
            version = pytesseract.get_tesseract_version()
            logger.info(f"Tesseract OCR initialized: version {version}")
        except Exception as e:
            logger.error(f"Tesseract not available: {e}")
            raise RuntimeError("Tesseract OCR is not installed or not accessible")
    
    def process_document(
        self,
        file_path: str,
        file_type: str,
        language: str = 'mixed',
        is_handwritten: bool = False
    ) -> Dict:
        """
        Process a document and extract text using OCR
        
        Args:
            file_path: Path to the document file
            file_type: File extension (.pdf, .jpg, etc.)
            language: Language hint ('ar', 'en', 'mixed')
            is_handwritten: Whether document contains handwriting
        
        Returns:
            Dict with extracted text, confidence, and metadata
        """
        extraction_start = timezone.now()
        
        # Determine tesseract language
        tesseract_lang = self._get_tesseract_lang(language)
        
        # Process based on file type
        if file_type.lower() == '.pdf':
            result = self._process_pdf(file_path, tesseract_lang, is_handwritten)
        elif file_type.lower() in SUPPORTED_IMAGE_TYPES:
            result = self._process_image(file_path, tesseract_lang, is_handwritten)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        extraction_end = timezone.now()
        
        # Add metadata
        result['extraction_timestamp'] = extraction_end.isoformat()
        result['processing_time_ms'] = int((extraction_end - extraction_start).total_seconds() * 1000)
        result['language_used'] = language
        result['tesseract_lang'] = tesseract_lang
        result['is_handwritten'] = is_handwritten
        result['ocr_engine'] = 'tesseract'
        result['ocr_version'] = str(pytesseract.get_tesseract_version())
        
        # Generate evidence hash
        result['evidence_hash'] = self._generate_evidence_hash(result)
        
        return result
    
    def _get_tesseract_lang(self, language: str) -> str:
        """Get tesseract language code"""
        if language == 'ar':
            return TESSERACT_LANG_ARABIC
        elif language == 'en':
            return TESSERACT_LANG_ENGLISH
        else:
            return TESSERACT_LANG_MIXED
    
    def _process_pdf(
        self,
        file_path: str,
        tesseract_lang: str,
        is_handwritten: bool
    ) -> Dict:
        """Process PDF document"""
        try:
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=300)
            
            all_text = []
            all_confidences = []
            page_results = []
            
            for page_num, image in enumerate(images, 1):
                page_result = self._extract_from_image(image, tesseract_lang, is_handwritten)
                page_result['page_number'] = page_num
                page_results.append(page_result)
                
                if page_result['text']:
                    all_text.append(page_result['text'])
                    all_confidences.append(page_result['confidence'])
            
            # Combine results
            combined_text = '\n\n'.join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            return {
                'text': combined_text,
                'text_ar': self._extract_arabic_text(combined_text),
                'text_en': self._extract_english_text(combined_text),
                'confidence': int(avg_confidence),
                'page_count': len(images),
                'pages': page_results,
                'document_type': 'pdf',
            }
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            return {
                'text': '',
                'text_ar': '',
                'text_en': '',
                'confidence': 0,
                'error': str(e),
                'document_type': 'pdf',
            }
    
    def _process_image(
        self,
        file_path: str,
        tesseract_lang: str,
        is_handwritten: bool
    ) -> Dict:
        """Process image document"""
        try:
            image = Image.open(file_path)
            result = self._extract_from_image(image, tesseract_lang, is_handwritten)
            result['document_type'] = 'image'
            result['page_count'] = 1
            return result
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            return {
                'text': '',
                'text_ar': '',
                'text_en': '',
                'confidence': 0,
                'error': str(e),
                'document_type': 'image',
            }
    
    def _extract_from_image(
        self,
        image: Image.Image,
        tesseract_lang: str,
        is_handwritten: bool
    ) -> Dict:
        """Extract text from a single image"""
        # Preprocess image for better OCR
        processed_image = self._preprocess_image(image, is_handwritten)
        
        # Configure tesseract
        custom_config = self._get_tesseract_config(is_handwritten)
        
        # Extract text with data (includes confidence)
        try:
            data = pytesseract.image_to_data(
                processed_image,
                lang=tesseract_lang,
                config=custom_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [int(c) for c in data['conf'] if int(c) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            # Get full text
            text = pytesseract.image_to_string(
                processed_image,
                lang=tesseract_lang,
                config=custom_config
            )
            
            return {
                'text': text.strip(),
                'text_ar': self._extract_arabic_text(text),
                'text_en': self._extract_english_text(text),
                'confidence': int(avg_confidence),
                'word_count': len([w for w in data['text'] if w.strip()]),
            }
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return {
                'text': '',
                'text_ar': '',
                'text_en': '',
                'confidence': 0,
                'error': str(e),
            }
    
    def _preprocess_image(self, image: Image.Image, is_handwritten: bool) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # For handwritten documents, apply additional preprocessing
        if is_handwritten:
            # Convert to grayscale
            image = image.convert('L')
            # Apply threshold for better contrast
            threshold = 180
            image = image.point(lambda p: 255 if p > threshold else 0)
            # Convert back to RGB
            image = image.convert('RGB')
        
        return image
    
    def _get_tesseract_config(self, is_handwritten: bool) -> str:
        """Get tesseract configuration"""
        if is_handwritten:
            # Use LSTM engine for handwriting (better for handwritten text)
            return '--oem 1 --psm 6'
        else:
            # Use default for printed text
            return '--oem 3 --psm 6'
    
    def _extract_arabic_text(self, text: str) -> str:
        """Extract Arabic text portions"""
        if not text:
            return ''
        # Arabic Unicode range: \u0600-\u06FF
        arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+[\s\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\d\.,،؛:]*')
        arabic_parts = arabic_pattern.findall(text)
        return ' '.join(arabic_parts).strip()
    
    def _extract_english_text(self, text: str) -> str:
        """Extract English text portions"""
        if not text:
            return ''
        # Remove Arabic characters
        english_pattern = re.compile(r'[a-zA-Z]+[\s\w\d\.,;:]*')
        english_parts = english_pattern.findall(text)
        return ' '.join(english_parts).strip()
    
    def _generate_evidence_hash(self, result: Dict) -> str:
        """Generate hash for evidence integrity"""
        hash_input = f"{result.get('text', '')}{result.get('extraction_timestamp', '')}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]
    
    def extract_structured_data(self, text: str, document_type: str) -> Dict:
        """
        Attempt to extract structured data from OCR text
        
        NOTE: This is best-effort extraction for audit purposes.
        Extracted values should NOT be treated as accounting truth.
        
        Returns:
            Dict with extracted values. Amounts are stored as Decimal for DB fields
            and as float for JSON serialization.
        """
        structured = {
            'invoice_number': None,
            'date': None,
            'total_amount': None,
            'tax_amount': None,
            'vendor_name': None,
            'vat_number': None,
            'confidence': 'low',
            'disclaimer': 'Extracted data is for audit reference only, not source of truth',
        }
        
        if not text:
            return structured
        
        # Try to extract invoice number
        invoice_patterns = [
            r'فاتورة\s*(?:رقم|#)?\s*[:\s]*(\d+)',
            r'Invoice\s*(?:No|#|Number)?[:\s]*(\w+[-/]?\w*)',
            r'رقم\s*الفاتورة[:\s]*(\d+)',
        ]
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                structured['invoice_number'] = match.group(1)
                break
        
        # Try to extract VAT number (Saudi format)
        vat_pattern = r'3\d{13}3'
        vat_match = re.search(vat_pattern, text)
        if vat_match:
            structured['vat_number'] = vat_match.group(0)
        
        # Try to extract amounts (store as Decimal for precision)
        amount_patterns = [
            r'(?:الإجمالي|المجموع|Total)[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'(?:المبلغ|Amount)[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    structured['total_amount'] = Decimal(amount_str)
                except:
                    pass
                break
        
        # Try to extract tax amount
        tax_patterns = [
            r'(?:الضريبة|ض\.?ق\.?م|VAT|Tax)[:\s]*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tax_str = match.group(1).replace(',', '')
                try:
                    structured['tax_amount'] = Decimal(tax_str)
                except:
                    pass
                break
        
        # Set confidence based on what was extracted
        extracted_count = sum(1 for v in [structured['invoice_number'], structured['total_amount'], structured['vat_number']] if v)
        if extracted_count >= 2:
            structured['confidence'] = 'medium'
        if extracted_count >= 3:
            structured['confidence'] = 'high'
        
        return structured
    
    def get_json_serializable_data(self, structured: Dict) -> Dict:
        """Convert structured data to JSON-serializable format"""
        json_safe = structured.copy()
        # Convert Decimal to float for JSON serialization
        if json_safe.get('total_amount') is not None:
            json_safe['total_amount'] = float(json_safe['total_amount'])
        if json_safe.get('tax_amount') is not None:
            json_safe['tax_amount'] = float(json_safe['tax_amount'])
        return json_safe
    
    def get_confidence_level(self, confidence: int) -> Tuple[str, str]:
        """Get confidence level description in Arabic and English"""
        if confidence >= OCRConfidence.HIGH:
            return ('مرتفعة', 'High')
        elif confidence >= OCRConfidence.MEDIUM:
            return ('متوسطة', 'Medium')
        elif confidence >= OCRConfidence.LOW:
            return ('منخفضة', 'Low')
        else:
            return ('ضعيفة جداً', 'Very Low')


# Singleton instance
document_ocr_service = DocumentOCRService()
