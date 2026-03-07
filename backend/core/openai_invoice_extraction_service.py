"""
OpenAI Invoice Extraction Service - Phase 1 AI OCR Pipeline
خدمة استخراج الفواتير من OpenAI

This service uses OpenAI Vision (gpt-4o-mini) to extract structured invoice data from documents.

Features:
- Vision-based invoice extraction
- Structured JSON output
- Supports Arabic and English invoices
- Automatic language detection
- Confidence scoring
- Graceful fallback to rule-based extraction if OpenAI fails
"""

import os
import base64
import json
import logging
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional, Any
import mimetypes

from django.conf import settings
from django.utils import timezone

try:
    from openai import OpenAI, APIError
except ImportError:
    OpenAI = None
    APIError = Exception

logger = logging.getLogger(__name__)


class OpenAIInvoiceExtractionService:
    """
    Service for extracting structured invoice data using OpenAI Vision API
    """
    
    # Invoice extraction schema
    INVOICE_SCHEMA = {
        "type": "object",
        "properties": {
            "invoice_number": {
                "type": "string",
                "description": "رقم الفاتورة / Invoice number"
            },
            "issue_date": {
                "type": "string",
                "description": "تاريخ الإصدار بصيغة YYYY-MM-DD / Issue date in YYYY-MM-DD format"
            },
            "due_date": {
                "type": "string",
                "description": "تاريخ الاستحقاق بصيغة YYYY-MM-DD / Due date in YYYY-MM-DD format"
            },
            "vendor_name": {
                "type": "string",
                "description": "اسم البائع / Vendor/Supplier name"
            },
            "vendor_tax_id": {
                "type": "string",
                "description": "رقم الضريبة للبائع / Vendor tax/VAT ID"
            },
            "customer_name": {
                "type": "string",
                "description": "اسم العميل / Customer/Bill To name"
            },
            "customer_tax_id": {
                "type": "string",
                "description": "رقم الضريبة للعميل / Customer tax/VAT ID"
            },
            "currency": {
                "type": "string",
                "description": "رمز العملة متل SAR, AED, USD / Currency code (SAR, AED, USD, etc.)"
            },
            "subtotal": {
                "type": "number",
                "description": "المجموع قبل الضريبة / Subtotal before tax"
            },
            "tax_amount": {
                "type": "number",
                "description": "مبلغ الضريبة / Tax amount"
            },
            "tax_rate": {
                "type": "number",
                "description": "معدل الضريبة كنسبة مئوية / Tax rate as percentage"
            },
            "total_amount": {
                "type": "number",
                "description": "المجموع النهائي / Total amount due"
            },
            "discount_amount": {
                "type": "number",
                "description": "مبلغ الخصم / Discount amount if any"
            },
            "items": {
                "type": "array",
                "description": "بنود الفاتورة / Line items",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "وصف البند / Item description"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "الكمية / Quantity"
                        },
                        "unit_price": {
                            "type": "number",
                            "description": "سعر الوحدة / Unit price"
                        },
                        "line_total": {
                            "type": "number",
                            "description": "إجمالي البند / Line total"
                        }
                    }
                }
            },
            "language_detected": {
                "type": "string",
                "description": "اللغة المكتشفة / Language detected (ar, en, mixed)"
            },
            "confidence": {
                "type": "number",
                "description": "درجة الثقة من 0 إلى 100 / Confidence score 0-100"
            }
        },
        "required": ["invoice_number", "vendor_name", "total_amount", "currency"]
    }
    
    def __init__(self):
        """Initialize the OpenAI client"""
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.client = None
        
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}")
                self.client = None
    
    def _encode_image_to_base64(self, file_path: str) -> str:
        """
        Encode image file to base64 for OpenAI Vision API
        """
        try:
            with open(file_path, 'rb') as image_file:
                return base64.standard_b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise
    
    def _get_media_type(self, file_path: str) -> str:
        """Get MIME type for the file"""
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Map common types to OpenAI accepted types
        type_mapping = {
            'application/pdf': 'application/pdf',
            'image/jpeg': 'image/jpeg',
            'image/png': 'image/png',
            'image/gif': 'image/gif',
            'image/webp': 'image/webp',
        }
        
        return type_mapping.get(mime_type, 'image/jpeg')
    
    def extract_invoice(self, file_path: str) -> Dict[str, Any]:
        """
        Extract invoice data from a document using OpenAI Vision API
        
        Args:
            file_path: Path to the document file
        
        Returns:
            Dictionary with extracted invoice data
        """
        if not self.client:
            logger.warning("OpenAI client not initialized, attempting fallback extraction")
            return self._fallback_extraction()
        
        try:
            media_type = self._get_media_type(file_path)
            
            # For PDFs, we need to handle them differently
            if media_type == 'application/pdf':
                return self._extract_from_pdf(file_path)
            
            # For images, encode and send to OpenAI
            image_data = self._encode_image_to_base64(file_path)
            
            extraction_prompt = """
            أنت خبير في تدقيق الفواتير المالية في دول الخليج.
            استخرج البيانات من هذه الفاتورة وأعدها بتنسيق JSON صارم فقط.
            يجب تحويل الأرقام العربية (١٢٣) إلى أرقام دولية (123).
            المخطط المطلوب:
            {
              "invoice_number": "",
              "issue_date": "YYYY-MM-DD",
              "due_date": "YYYY-MM-DD",
              "vendor_name": "",
              "vendor_tax_id": "",
              "customer_name": "",
              "customer_tax_id": "",
              "items": [
                {"description": "", "quantity": 0, "unit_price": 0.0, "line_total": 0.0}
              ],
              "subtotal": 0.0,
              "tax_amount": 0.0,
              "tax_rate": 0.0,
              "discount_amount": 0.0,
              "total_amount": 0.0,
              "currency": "SAR/AED/USD",
              "language_detected": "ar/en/mixed",
              "confidence": 0
            }
            لا تشرح شيئاً، أعد JSON فقط.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": extraction_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            },
                        ]
                    }
                ]
            )

            # Parse the response — response_format=json_object guarantees valid JSON
            extracted_data = json.loads(response.choices[0].message.content)
            extracted_data = self._validate_math(extracted_data)
            
            # Add metadata
            extracted_data['extraction_success'] = True
            extracted_data['extraction_engine'] = 'openai_gpt4o_mini'
            extracted_data['extraction_timestamp'] = datetime.now().isoformat()
            extracted_data['model_used'] = self.model
            
            logger.info(f"Successfully extracted invoice: {extracted_data.get('invoice_number', 'N/A')}")
            return extracted_data
            
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return self._fallback_extraction()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            return self._fallback_extraction()
        except Exception as e:
            logger.error(f"Error during invoice extraction: {e}")
            return self._fallback_extraction()
    
    def _extract_from_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extract from PDF — convert first page to JPEG in memory and send to Vision API.
        Uses BytesIO to avoid writing temp files to disk.
        """
        try:
            from pdf2image import convert_from_bytes

            logger.info(f"Converting PDF to image (in-memory) for extraction: {file_path}")

            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()

            images = convert_from_bytes(pdf_bytes, first_page=1, last_page=1)
            if not images:
                logger.warning("No images extracted from PDF")
                return self._fallback_extraction()

            # Encode first page to JPEG base64 in memory
            buffered = BytesIO()
            images[0].save(buffered, format="JPEG")
            image_data = base64.b64encode(buffered.getvalue()).decode('utf-8')

            extraction_prompt = """
            أنت خبير في تدقيق الفواتير المالية في دول الخليج.
            استخرج البيانات من هذه الفاتورة وأعدها بتنسيق JSON صارم فقط.
            يجب تحويل الأرقام العربية (١٢٣) إلى أرقام دولية (123).
            المخطط المطلوب:
            {
              "invoice_number": "",
              "issue_date": "YYYY-MM-DD",
              "due_date": "YYYY-MM-DD",
              "vendor_name": "",
              "vendor_tax_id": "",
              "customer_name": "",
              "customer_tax_id": "",
              "items": [
                {"description": "", "quantity": 0, "unit_price": 0.0, "line_total": 0.0}
              ],
              "subtotal": 0.0,
              "tax_amount": 0.0,
              "tax_rate": 0.0,
              "discount_amount": 0.0,
              "total_amount": 0.0,
              "currency": "SAR/AED/USD",
              "language_detected": "ar/en/mixed",
              "confidence": 0
            }
            لا تشرح شيئاً، أعد JSON فقط.
            """

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": extraction_prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                            },
                        ],
                    }
                ],
            )

            extracted_data = json.loads(response.choices[0].message.content)
            extracted_data = self._validate_math(extracted_data)

            extracted_data['extraction_success'] = True
            extracted_data['extraction_engine'] = 'openai_gpt4o_mini'
            extracted_data['extraction_timestamp'] = datetime.now().isoformat()
            extracted_data['model_used'] = self.model

            logger.info(f"PDF extraction complete: {extracted_data.get('invoice_number', 'N/A')}")
            return extracted_data

        except ImportError:
            logger.warning("pdf2image not available, falling back to text extraction")
            return self._fallback_extraction()
        except Exception as e:
            logger.error(f"Error converting PDF: {e}")
            return self._fallback_extraction()

    def _validate_math(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that total_amount matches the sum of line item totals."""
        try:
            total = Decimal(str(data.get('total_amount') or 0))
            items_sum = sum(
                Decimal(str(item.get('line_total') or item.get('total') or 0))
                for item in data.get('items', [])
            )
            data['is_mathematically_correct'] = (total == items_sum) if items_sum else None
        except Exception:
            data['is_mathematically_correct'] = False
        return data
    
    def _fallback_extraction(self) -> Dict[str, Any]:
        """
        Fallback extraction method when OpenAI is unavailable
        Returns a template with extraction_success=False
        """
        return {
            "extraction_success": False,
            "extraction_engine": "fallback",
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
            "error": "OpenAI extraction unavailable, please manually verify"
        }


# Singleton instance
_extraction_service = None


def get_openai_extraction_service() -> OpenAIInvoiceExtractionService:
    """Get or create singleton instance of OpenAI extraction service"""
    global _extraction_service
    if _extraction_service is None or _extraction_service.client is None:
        _extraction_service = OpenAIInvoiceExtractionService()
    return _extraction_service
