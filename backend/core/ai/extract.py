"""
Structured Data Extraction - JSON schema-based extraction from text/images

Extracts:
- Invoice data (vendor, invoice number, amounts, line items)
- Accounting entries (journal entry suggestions)
- Any other structured data with schema validation
"""
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from .client import get_openai_client
from .errors import FileProcessingError, ValidationError, AIAPIError
from .utils import validate_json_response
from .constants import INVOICE_EXTRACTION_SCHEMA

logger = logging.getLogger(__name__)


class StructuredExtractor:
    """Extract structured data (JSON) from documents."""
    
    def __init__(self):
        """Initialize extractor."""
        self.client = get_openai_client()
    
    def extract_invoice_data(
        self,
        ocr_text: str,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Extract invoice data from OCR text.
        
        Args:
            ocr_text: Extracted text from document (from OCR)
            language: Document language (ar/en)
            
        Returns:
            Dict with:
            - extracted_data: Structured invoice data
            - confidence: Confidence score (0-1)
            - warnings: Any issues found
            - raw_response: Raw AI response for audit
            
        Raises:
            FileProcessingError: Validation error
            AIAPIError: OpenAI API error
        """
        logger.info("Extracting invoice data from OCR text")
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            logger.warning("OCR text too short for extraction")
            raise FileProcessingError("Document text too short to extract invoice data")
        
        # Build extraction prompt
        lang_name = "Arabic" if language == 'ar' else "English"
        
        prompt = f"""You are an expert financial document analyst. 
Extract structured invoice data from the following document text ({lang_name}).

IMPORTANT JSON SCHEMA:
{{
  "vendor_name": "Company/person who issued invoice",
  "vendor_vat_number": "VAT/Tax ID of vendor (format: 3XXXXXXXXXX00003 for Saudi)",
  "invoice_number": "Unique invoice identifier",
  "invoice_date": "Date invoice was issued (YYYY-MM-DD)",
  "due_date": "Payment due date (YYYY-MM-DD) if available",
  "customer_name": "Name of customer/buyer",
  "line_items": [
    {{
      "description": "Item description",
      "quantity": 1,
      "unit_price": 100.00,
      "tax_rate": 0.15,
      "line_total": 115.00
    }}
  ],
  "subtotal": 1000.00,
  "tax_amount": 150.00,
  "total": 1150.00,
  "currency": "SAR",
  "payment_method": "Transfer/Cash/Cheque if available",
  "notes": "Any additional notes or remarks"
}}

EXTRACTION RULES:
1. Extract ONLY data that is explicitly mentioned in the document
2. Leave fields as null if not found (do NOT guess or invent data)
3. For amounts: extract exact numbers from document
4. For dates: convert to YYYY-MM-DD format
5. For line items: extract each individual item with qty, price, and calculated totals
6. For Saudi VAT: Format is always 3 + 13 digits + 3 (e.g., 3XXXXXXXXXX00003)
7. Return ONLY valid JSON, no other text

CRITICAL: Return a JSON object (not string, not markdown, pure JSON).
"""
        
        try:
            # Call OpenAI
            response = self.client.text_extract(
                text=ocr_text,
                prompt=prompt,
                temperature=0.1  # Low temperature for accuracy
            )
            
            logger.debug(f"Extraction API response: {response[:200]}...")
            
            # Parse JSON response
            extracted_data = self._parse_json_response(response)
            
            # Validate against schema
            required_fields_found = self._count_required_fields(extracted_data)
            confidence = required_fields_found / 5  # 5 critical fields
            confidence = min(max(confidence, 0.3), 1.0)
            
            # Check for warnings
            warnings = self._validate_extracted_data(extracted_data)
            
            return {
                'extracted_data': extracted_data,
                'confidence': confidence,
                'warnings': warnings,
                'raw_response': response,
                'timestamp': datetime.now().isoformat(),
                'method': 'openai_vision',
            }
        
        except json.JSONDecodeError:
            logger.error("Failed to parse extraction JSON response")
            raise FileProcessingError(
                "Failed to parse AI response as JSON. Document may be invalid.",
                file_path="ocr_text"
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            raise AIAPIError(f"Invoice extraction failed: {str(e)}")
    
    def extract_accounting_entries(
        self,
        ocr_text: str,
        language: str = 'ar',
        company_vat: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract suggested accounting journal entries from document.
        
        Args:
            ocr_text: Extracted OCR text
            language: Document language
            company_vat: Company's VAT number (for purchase/sales classification)
            
        Returns:
            Dict with:
            - entries: List of suggested journal entries
            - total_debit: Sum of debit amounts
            - total_credit: Sum of credit amounts
            - confidence: Confidence score
            - warnings: Issues found
        """
        logger.info("Extracting accounting entries from document")
        
        prompt = f"""You are a professional accountant. Based on the following document, 
suggest accounting journal entries in {language} format.

JOURNAL ENTRY FORMAT (return as JSON):
{{
  "entries": [
    {{
      "date": "YYYY-MM-DD",
      "description_ar": "وصف المعامل بالعربية",
      "description_en": "Transaction description in English",
      "lines": [
        {{
          "account_name": "Account name",
          "account_code": "Code if known",
          "debit": 0,
          "credit": 1000,
          "narration": "Brief explanation"
        }}
      ]
    }}
  ],
  "total_debit": 1000,
  "total_credit": 1000,
  "notes": "Any assumptions or recommendations"
}}

RULES:
1. Debit = Debit side (left), Credit = Credit side (right)
2. Each entry must balance: total_debit == total_credit
3. Use standard accounting accounts if known
4. Include VAT entries if applicable
5. Suggest but CLEARLY mark as "TENTATIVE" if document is unclear
6. Return VALID JSON ONLY

Document text to analyze:
"""
        
        try:
            response = self.client.text_extract(
                text=ocr_text,
                prompt=prompt,
                temperature=0.2
            )
            
            entries_data = self._parse_json_response(response)
            
            # Validate entries balance
            warnings = self._validate_entries_balance(entries_data)
            
            confidence = 0.7 if not warnings else 0.5
            
            return {
                'entries': entries_data.get('entries', []),
                'total_debit': entries_data.get('total_debit', 0),
                'total_credit': entries_data.get('total_credit', 0),
                'confidence': confidence,
                'warnings': warnings,
                'raw_response': response,
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Accounting extraction failed: {e}")
            raise AIAPIError(f"Failed to extract accounting entries: {str(e)}")
    
    def extract_with_schema(
        self,
        ocr_text: str,
        extraction_schema: Dict[str, Any],
        instructions: str,
        language: str = 'ar'
    ) -> Dict[str, Any]:
        """
        Generic extraction with custom schema.
        
        Args:
            ocr_text: Text to extract from
            extraction_schema: JSON schema for validation
            instructions: Detailed extraction instructions
            language: Document language
            
        Returns:
            Dict with extracted data
        """
        logger.info("Extracting with custom schema")
        
        prompt = f"""{instructions}

Return ONLY valid JSON matching this schema:
{json.dumps(extraction_schema, indent=2)}

Document language: {language}
Do NOT add explanations or markdown - return pure JSON only.
"""
        
        try:
            response = self.client.text_extract(
                text=ocr_text,
                prompt=prompt,
                temperature=0.1
            )
            
            extracted = self._parse_json_response(response)
            
            return {
                'extracted_data': extracted,
                'confidence': 0.75,
                'raw_response': response,
                'timestamp': datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"Custom extraction failed: {e}")
            raise AIAPIError(f"Extraction failed: {str(e)}")
    
    # ===== Helper Methods =====
    
    def _parse_json_response(self, response: str) -> dict:
        """Parse JSON from API response, handling markdown formatting."""
        response = response.strip()
        
        # Remove markdown JSON blocks if present
        if response.startswith('```'):
            response = response.split('```')[1]
            if response.startswith('json'):
                response = response[4:]
            response = response.strip()
        
        return json.loads(response)
    
    def _count_required_fields(self, data: dict) -> int:
        """Count required fields found in extracted data."""
        required = ['vendor_name', 'invoice_number', 'invoice_date', 'total', 'currency']
        count = sum(1 for field in required if data.get(field))
        return count
    
    def _validate_extracted_data(self, data: dict) -> List[str]:
        """Validate extracted invoice data."""
        warnings = []
        
        # Check VAT number format if present
        if data.get('vendor_vat_number'):
            vat = data['vendor_vat_number'].replace(' ', '')
            if not (len(vat) == 15 and vat.startswith('3') and vat.endswith('3')):
                warnings.append(f"VAT number format may be invalid: {vat}")
        
        # Check date formats
        for date_field in ['invoice_date', 'due_date']:
            if data.get(date_field):
                try:
                    datetime.strptime(str(data[date_field]), '%Y-%m-%d')
                except ValueError:
                    warnings.append(f"Invalid date format for {date_field}: {data[date_field]}")
        
        # Check amounts
        if data.get('line_items'):
            subtotal_check = sum(item.get('line_total', 0) for item in data['line_items'])
            if subtotal_check > 0 and data.get('subtotal'):
                if abs(subtotal_check - data['subtotal']) > 1:  # Allow 1 unit rounding error
                    warnings.append(f"Subtotal mismatch: items sum to {subtotal_check}, declared {data['subtotal']}")
        
        # Check VAT calculation
        if data.get('subtotal') and data.get('tax_amount') and data.get('total'):
            expected_total = data['subtotal'] + data['tax_amount']
            if abs(expected_total - data['total']) > 1:
                warnings.append(f"Total mismatch: {data['subtotal']} + {data['tax_amount']} != {data['total']}")
        
        return warnings
    
    def _validate_entries_balance(self, entries_data: dict) -> List[str]:
        """Validate journal entries balance."""
        warnings = []
        
        total_debit = entries_data.get('total_debit', 0)
        total_credit = entries_data.get('total_credit', 0)
        
        if abs(total_debit - total_credit) > 0.01:
            warnings.append(f"Entries don't balance: Debit={total_debit}, Credit={total_credit}")
        
        return warnings
