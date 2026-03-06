"""
OCR Processing - Document text extraction with fallback strategy

Strategy:
1. If PDF: Convert to images (limit pages) + use vision model
2. If image: Use vision model directly
3. If vision fails: Fallback to Tesseract local OCR
4. Return: extracted_text, language, confidence, method_used
"""
import logging
import json
from typing import Dict, Optional
from datetime import datetime

from .client import get_openai_client
from .errors import FileProcessingError, AIAPIError
from .utils import (
    validate_file_size,
    detect_file_type,
    encode_file_to_base64,
    is_pdf,
    is_image,
    get_file_info,
    limit_pdf_pages,
)
from .constants import (
    ERRORS_EN,
    OCR_MIN_CONFIDENCE,
    TESSERACT_TIMEOUT,
    VISION_API_TIMEOUT,
)

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Document OCR with vision model and Tesseract fallback."""
    
    def __init__(self):
        """Initialize OCR processor."""
        self.client = get_openai_client()
        self.tesseract_available = self._check_tesseract()
    
    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        try:
            import pytesseract
            pytesseract.pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR available as fallback")
            return True
        except Exception as e:
            logger.warning(f"Tesseract not available: {e}. Vision API will be primary method.")
            return False
    
    def process(
        self,
        file_path: str,
        language_hint: str = 'ar'
    ) -> Dict[str, any]:
        """
        Process document and extract text.
        
        Args:
            file_path: Full path to document on disk
            language_hint: Language hint (ar/en/mixed)
            
        Returns:
            Dict with:
            - extracted_text: Extracted text content
            - language: Detected language
            - confidence: Confidence score (0-1)
            - method: 'vision', 'tesseract', or 'mixed'
            - pages: Page count (for PDFs)
            - processing_time_ms: Time taken
            - timestamp: When processed
            
        Raises:
            FileProcessingError: Validation or processing error
            AIAPIError: OpenAI API error
        """
        start_time = datetime.now()
        
        try:
            # Validate file
            validate_file_size(file_path)
            ext, mime_type = detect_file_type(file_path)
            file_info = get_file_info(file_path)
            
            logger.info(f"Processing document: {file_info}")
            
            # Route based on file type
            if is_pdf(file_path):
                result = self._process_pdf(file_path, language_hint)
            elif is_image(file_path):
                result = self._process_image(file_path, language_hint)
            else:
                raise FileProcessingError(
                    ERRORS_EN['unsupported_type'].format(file_type=ext, allowed='pdf, jpeg, png'),
                    file_path=file_path,
                    file_type=ext
                )
            
            # Calculate processing time
            elapsed_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            result['processing_time_ms'] = elapsed_ms
            result['timestamp'] = start_time.isoformat()
            
            logger.info(f"OCR completed: {elapsed_ms}ms, method={result.get('method')}, "
                       f"confidence={result.get('confidence')}")
            
            return result
        
        except (FileProcessingError, AIAPIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OCR: {e}")
            raise FileProcessingError(f"OCR processing failed: {str(e)}", file_path=file_path)
    
    def _process_pdf(self, file_path: str, language_hint: str) -> Dict[str, any]:
        """Process PDF file."""
        logger.info(f"Processing PDF: {file_path}")
        
        # Limit pages to prevent memory issues
        limited_file = limit_pdf_pages(file_path)
        
        # Convert PDF to images for vision processing
        try:
            from pdf2image import convert_from_path
            
            images = convert_from_path(limited_file, first_page=1, last_page=20, dpi=150)
            logger.info(f"Converted PDF to {len(images)} images")
            
            # Process with vision model
            all_text = []
            all_confidences = []
            
            for page_num, image in enumerate(images, 1):
                # Save image temporarily for encoding
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    image.save(tmp.name, 'JPEG')
                    temp_image_path = tmp.name
                
                try:
                    page_result = self._process_single_image(
                        temp_image_path,
                        language_hint,
                        page_num
                    )
                    
                    if page_result.get('extracted_text'):
                        all_text.append(page_result['extracted_text'])
                        all_confidences.append(page_result.get('confidence', 0.5))
                
                finally:
                    import os
                    try:
                        os.remove(temp_image_path)
                    except:
                        pass
            
            # Combine results
            combined_text = '\n\n--- Page Break ---\n\n'.join(all_text)
            avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
            
            return {
                'extracted_text': combined_text,
                'language': language_hint,
                'confidence': avg_confidence,
                'method': 'vision',
                'pages': len(images),
                'is_pdf': True,
            }
        
        except Exception as e:
            logger.error(f"Failed to process PDF with vision: {e}")
            if self.tesseract_available:
                logger.info("Falling back to Tesseract for PDF...")
                return self._process_pdf_tesseract(file_path, language_hint)
            raise AIAPIError(f"PDF processing failed: {str(e)}")
    
    def _process_image(self, file_path: str, language_hint: str) -> Dict[str, any]:
        """Process single image file."""
        logger.info(f"Processing image: {file_path}")
        
        result = self._process_single_image(file_path, language_hint)
        result['is_pdf'] = False
        return result
    
    def _process_single_image(
        self,
        file_path: str,
        language_hint: str,
        page_num: int = 1
    ) -> Dict[str, any]:
        """Process single image with vision API."""
        try:
            # Encode image to base64
            image_base64 = encode_file_to_base64(file_path)
            
            # Build OCR prompt
            language_str = "Arabic" if language_hint == 'ar' else "English" if language_hint == 'en' else "Arabic and English"
            
            prompt = f"""Please extract ALL text from this document image. 
The document may be in {language_str} or a mix of languages.

Requirements:
1. Extract EVERY word and number visible
2. Preserve the document structure and layout as much as possible
3. Identify the primary language(s) used
4. Note any handwritten vs printed text
5. Return the extracted text in the response

If the image is unclear or partially visible, extract what you can and note any illegible areas."""
            
            # Call OpenAI vision API
            response = self.client.vision_extract(
                image_base64=image_base64,
                prompt=prompt,
                temperature=0.1
            )
            
            logger.debug(f"Vision API response (page {page_num}): {len(response)} chars")
            
            # Parse response
            extracted_text = response.strip()
            
            # Simple confidence scoring based on response length
            confidence = min(len(extracted_text.split()) / 10, 1.0)  # More words = more confident
            confidence = max(confidence, 0.4)  # Minimum 40%
            
            return {
                'extracted_text': extracted_text,
                'language': language_hint,
                'confidence': confidence,
                'method': 'vision',
                'page_number': page_num,
            }
        
        except Exception as e:
            logger.error(f"Vision API failed for page {page_num}: {e}")
            
            # Try Tesseract fallback
            if self.tesseract_available:
                logger.info(f"Falling back to Tesseract for page {page_num}...")
                return self._process_image_tesseract(file_path, language_hint, page_num)
            
            raise AIAPIError(f"Image processing failed: {str(e)}")
    
    def _process_pdf_tesseract(self, file_path: str, language_hint: str) -> Dict[str, any]:
        """Fallback PDF processing with Tesseract."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            lang = self._get_tesseract_lang(language_hint)
            
            images = convert_from_path(file_path, first_page=1, last_page=20, dpi=100)
            
            all_text = []
            try:
                for image in images:
                    text = pytesseract.image_to_string(image, lang=lang)
                    if text.strip():
                        all_text.append(text)
            except pytesseract.TesseractNotFoundError:
                raise FileProcessingError(ERRORS_EN['ocr_failed'].format(error="Tesseract not found"))
            
            combined_text = '\n\n'.join(all_text)
            
            return {
                'extracted_text': combined_text,
                'language': language_hint,
                'confidence': 0.5,  # Tesseract fallback is lower confidence
                'method': 'tesseract',
                'pages': len(images),
                'is_pdf': True,
            }
        
        except Exception as e:
            logger.error(f"Tesseract PDF processing failed: {e}")
            raise FileProcessingError(ERRORS_EN['ocr_failed'].format(error=str(e)))
    
    def _process_image_tesseract(
        self,
        file_path: str,
        language_hint: str,
        page_num: int = 1
    ) -> Dict[str, any]:
        """Fallback image processing with Tesseract."""
        try:
            import pytesseract
            from PIL import Image
            
            lang = self._get_tesseract_lang(language_hint)
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image, lang=lang)
            
            return {
                'extracted_text': text.strip(),
                'language': language_hint,
                'confidence': 0.5,
                'method': 'tesseract',
                'page_number': page_num,
            }
        
        except Exception as e:
            logger.error(f"Tesseract image processing failed: {e}")
            raise FileProcessingError(ERRORS_EN['ocr_failed'].format(error=str(e)))
    
    def _get_tesseract_lang(self, language_hint: str) -> str:
        """Get Tesseract language code."""
        if language_hint == 'ar':
            return 'ara'
        elif language_hint == 'en':
            return 'eng'
        else:
            return 'ara+eng'
