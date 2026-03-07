"""
OpenAI Vision Invoice Extraction Service

This service uses OpenAI's Vision API (gpt-4o-mini) to extract structured
invoice data from image documents (jpg, jpeg, png).

Features:
- Base64 image encoding
- Structured JSON output with strict schema
- Fallback support for OCR errors
- Comprehensive error logging
- Confidence scoring

Schema:
{
  "invoice_number": "",
  "issue_date": "",
  "due_date": "",
  "vendor": {
    "name": "",
    "address": "",
    "city": "",
    "country": ""
  },
  "customer": {
    "name": "",
    "address": "",
    "city": "",
    "country": "",
    "tin": ""
  },
  "items": [
    {
      "product": "",
      "description": "",
      "quantity": "",
      "unit_price": "",
      "discount": "",
      "total": ""
    }
  ],
  "total_amount": "",
  "currency": ""
}
"""

import os
import base64
import logging
import json
from typing import Dict, Optional, Tuple
from django.utils import timezone
import requests
from io import BytesIO
from PIL import Image

logger = logging.getLogger(__name__)


class OpenAIInvoiceExtractionError(Exception):
    """Base exception for OpenAI invoice extraction"""
    pass


class OpenAIInvoiceService:
    """
    Invoice extraction using OpenAI Vision API (gpt-4o-mini)
    """
    
    MODEL = "gpt-4o-mini"
    MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
    SUPPORTED_FORMATS = {'jpg', 'jpeg', 'png'}
    
    def __init__(self):
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not set in environment")
        self.api_base = "https://api.openai.com/v1"
    
    def is_available(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(self.api_key)
    
    def extract_invoice_from_file(
        self,
        file_path: str
    ) -> Dict:
        """
        Extract invoice data from a file path.
        
        Args:
            file_path: Path to the invoice image file
            
        Returns:
            Dict with:
            - success: bool
            - extracted_data: dict (invoice JSON) or None
            - confidence: int (0-100)
            - raw_response: str (API response for audit)
            - error: str or None
            - processing_time_ms: int
        """
        start_time = timezone.now()
        
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': f"File not found: {file_path}",
                    'processing_time_ms': int(
                        (timezone.now() - start_time).total_seconds() * 1000
                    )
                }
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if file_ext not in self.SUPPORTED_FORMATS:
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': f"Unsupported image format: {file_ext}",
                    'processing_time_ms': int(
                        (timezone.now() - start_time).total_seconds() * 1000
                    )
                }
            
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_IMAGE_SIZE:
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': f"Image too large: {file_size} bytes (max {self.MAX_IMAGE_SIZE})",
                    'processing_time_ms': int(
                        (timezone.now() - start_time).total_seconds() * 1000
                    )
                }
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                image_bytes = f.read()
            
            base64_image = base64.standard_b64encode(image_bytes).decode('utf-8')
            
            # Call OpenAI Vision API
            result = self._call_openai_vision(base64_image, file_ext)
            
            processing_time = int(
                (timezone.now() - start_time).total_seconds() * 1000
            )
            result['processing_time_ms'] = processing_time
            
            return result
            
        except Exception as e:
            error_msg = f"OpenAI invoice extraction error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'extracted_data': None,
                'confidence': 0,
                'raw_response': None,
                'error': error_msg,
                'processing_time_ms': int(
                    (timezone.now() - start_time).total_seconds() * 1000
                )
            }
    
    def extract_invoice_from_bytes(
        self,
        image_bytes: bytes,
        file_ext: str = 'jpg'
    ) -> Dict:
        """
        Extract invoice data from image bytes.
        
        Args:
            image_bytes: Image bytes (jpg, jpeg, or png)
            file_ext: File extension (jpg, jpeg, png)
            
        Returns:
            Dict with extracted invoice data and metadata
        """
        start_time = timezone.now()
        
        try:
            # Validate format
            if file_ext.lower() not in self.SUPPORTED_FORMATS:
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': f"Unsupported image format: {file_ext}",
                    'processing_time_ms': int(
                        (timezone.now() - start_time).total_seconds() * 1000
                    )
                }
            
            # Check size
            if len(image_bytes) > self.MAX_IMAGE_SIZE:
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': f"Image too large: {len(image_bytes)} bytes (max {self.MAX_IMAGE_SIZE})",
                    'processing_time_ms': int(
                        (timezone.now() - start_time).total_seconds() * 1000
                    )
                }
            
            # Encode
            base64_image = base64.standard_b64encode(image_bytes).decode('utf-8')
            
            # Call API
            result = self._call_openai_vision(base64_image, file_ext)
            
            processing_time = int(
                (timezone.now() - start_time).total_seconds() * 1000
            )
            result['processing_time_ms'] = processing_time
            
            return result
            
        except Exception as e:
            error_msg = f"OpenAI invoice extraction error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'extracted_data': None,
                'confidence': 0,
                'raw_response': None,
                'error': error_msg,
                'processing_time_ms': int(
                    (timezone.now() - start_time).total_seconds() * 1000
                )
            }
    
    def _call_openai_vision(
        self,
        base64_image: str,
        file_ext: str = 'jpg'
    ) -> Dict:
        """
        Call OpenAI Vision API with base64 encoded image.
        
        Args:
            base64_image: Base64 encoded image string
            file_ext: File extension (jpg, jpeg, png)
            
        Returns:
            Dict with extracted data or error
        """
        if not self.api_key:
            return {
                'success': False,
                'extracted_data': None,
                'confidence': 0,
                'raw_response': None,
                'error': 'OPENAI_API_KEY not configured'
            }
        
        try:
            # Map file extension to media type
            media_type_map = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png'
            }
            media_type = media_type_map.get(file_ext.lower(), 'image/jpeg')
            
            # Prepare the prompt
            extraction_prompt = """
You are an expert invoice data extraction system. Your task is to extract structured data from an invoice image.

Extract the following information EXACTLY as shown in the invoice and return ONLY valid JSON (no markdown, no code blocks, no comments).

IMPORTANT RULES:
1. Return ONLY the JSON object, nothing else
2. Preserve exact values from the invoice
3. Leave fields empty strings if not found
4. Format numbers as strings (don't convert to numbers)
5. For dates, use ISO format (YYYY-MM-DD) if possible, otherwise return as found

Return this exact JSON schema:
{
  "invoice_number": "",
  "issue_date": "",
  "due_date": "",
  "vendor": {
    "name": "",
    "address": "",
    "city": "",
    "country": ""
  },
  "customer": {
    "name": "",
    "address": "",
    "city": "",
    "country": "",
    "tin": ""
  },
  "items": [
    {
      "product": "",
      "description": "",
      "quantity": "",
      "unit_price": "",
      "discount": "",
      "total": ""
    }
  ],
  "total_amount": "",
  "currency": ""
}

Extract all data from the invoice image now.
"""
            
            # Call OpenAI API
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                "model": self.MODEL,
                "messages": [
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
                                    "url": f"data:{media_type};base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.0  # Deterministic extraction
            }
            
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            response_json = response.json()
            
            # Extract the content
            if response_json.get('choices') and len(response_json['choices']) > 0:
                message_content = response_json['choices'][0].get('message', {}).get('content', '')
                
                # Parse JSON response
                try:
                    # Clean the response (remove markdown code blocks if present)
                    cleaned_content = message_content.strip()
                    if cleaned_content.startswith('```json'):
                        cleaned_content = cleaned_content[7:]
                    if cleaned_content.startswith('```'):
                        cleaned_content = cleaned_content[3:]
                    if cleaned_content.endswith('```'):
                        cleaned_content = cleaned_content[:-3]
                    cleaned_content = cleaned_content.strip()
                    
                    extracted_json = json.loads(cleaned_content)
                    
                    # Validate schema
                    extracted_json = self._validate_schema(extracted_json)
                    
                    # Calculate confidence based on filled fields
                    confidence = self._calculate_confidence(extracted_json)
                    
                    logger.info(f"Successfully extracted invoice with {confidence}% confidence")
                    
                    return {
                        'success': True,
                        'extracted_data': extracted_json,
                        'confidence': confidence,
                        'raw_response': message_content,
                        'error': None
                    }
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse OpenAI JSON response: {e}")
                    logger.error(f"Raw response: {message_content}")
                    return {
                        'success': False,
                        'extracted_data': None,
                        'confidence': 0,
                        'raw_response': message_content,
                        'error': f"Invalid JSON response from OpenAI: {str(e)}"
                    }
            else:
                logger.error("No choices in OpenAI response")
                return {
                    'success': False,
                    'extracted_data': None,
                    'confidence': 0,
                    'raw_response': None,
                    'error': 'No response from OpenAI'
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"OpenAI API request error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'extracted_data': None,
                'confidence': 0,
                'raw_response': None,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Unexpected error in OpenAI vision call: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                'success': False,
                'extracted_data': None,
                'confidence': 0,
                'raw_response': None,
                'error': error_msg
            }
    
    def _validate_schema(self, data: Dict) -> Dict:
        """
        Validate and ensure extracted data matches expected schema.
        
        Args:
            data: Extracted JSON data from OpenAI
            
        Returns:
            Validated data dict with all required fields
        """
        # Define the schema with defaults
        schema = {
            "invoice_number": "",
            "issue_date": "",
            "due_date": "",
            "vendor": {
                "name": "",
                "address": "",
                "city": "",
                "country": ""
            },
            "customer": {
                "name": "",
                "address": "",
                "city": "",
                "country": "",
                "tin": ""
            },
            "items": [],
            "total_amount": "",
            "currency": ""
        }
        
        # Merge with provided data
        if isinstance(data, dict):
            # Top-level fields
            for key in ['invoice_number', 'issue_date', 'due_date', 'total_amount', 'currency']:
                if key in data and data[key]:
                    schema[key] = str(data[key])
            
            # Vendor
            if isinstance(data.get('vendor'), dict):
                for key in ['name', 'address', 'city', 'country']:
                    if key in data['vendor'] and data['vendor'][key]:
                        schema['vendor'][key] = str(data['vendor'][key])
            
            # Customer
            if isinstance(data.get('customer'), dict):
                for key in ['name', 'address', 'city', 'country', 'tin']:
                    if key in data['customer'] and data['customer'][key]:
                        schema['customer'][key] = str(data['customer'][key])
            
            # Items
            if isinstance(data.get('items'), list):
                schema['items'] = []
                for item in data['items']:
                    if isinstance(item, dict):
                        validated_item = {
                            "product": str(item.get('product', '')),
                            "description": str(item.get('description', '')),
                            "quantity": str(item.get('quantity', '')),
                            "unit_price": str(item.get('unit_price', '')),
                            "discount": str(item.get('discount', '')),
                            "total": str(item.get('total', ''))
                        }
                        schema['items'].append(validated_item)
        
        return schema
    
    def _calculate_confidence(self, extracted_data: Dict) -> int:
        """
        Calculate confidence score based on extracted fields.
        
        Args:
            extracted_data: Extracted invoice data
            
        Returns:
            Confidence score (0-100)
        """
        score = 0
        total_fields = 0
        filled_fields = 0
        
        # Check main fields
        main_fields = ['invoice_number', 'issue_date', 'vendor', 'customer', 'total_amount']
        total_fields += len(main_fields)
        
        for field in main_fields:
            if field in extracted_data and extracted_data[field]:
                if isinstance(extracted_data[field], dict):
                    # Check if vendor/customer has at least one field
                    if any(extracted_data[field].values()):
                        filled_fields += 1
                else:
                    filled_fields += 1
        
        # Check items
        total_fields += 1
        if extracted_data.get('items') and len(extracted_data['items']) > 0:
            filled_fields += 1
        
        # Calculate percentage
        if total_fields > 0:
            score = int((filled_fields / total_fields) * 100)
        
        return max(0, min(100, score))


# Singleton instance
_openai_invoice_service = None


def get_openai_invoice_service() -> OpenAIInvoiceService:
    """Get or create the OpenAI invoice service instance"""
    global _openai_invoice_service
    if _openai_invoice_service is None:
        _openai_invoice_service = OpenAIInvoiceService()
    return _openai_invoice_service
