"""
Invoice Normalization Service - Phase 2

This service normalizes extracted invoice data to ensure consistency:
- Dates to YYYY-MM-DD format
- Numbers to Decimal type
- Currency codes standardized
- Null/empty values cleaned
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class InvoiceNormalizationService:
    """
    Normalize extracted invoice data to consistent format
    """
    
    # Common currency symbols and codes
    CURRENCY_MAP = {
        'usd': 'USD',
        '$': 'USD',
        'eur': 'EUR',
        '€': 'EUR',
        'gbp': 'GBP',
        '£': 'GBP',
        'sar': 'SAR',
        'ريال سعودي': 'SAR',
        'aed': 'AED',
        'د.إ': 'AED',
        'jpy': 'JPY',
        '¥': 'JPY',
    }
    
    # ISO 8601 date format
    DATE_FORMAT = '%Y-%m-%d'
    
    @staticmethod
    def normalize_date(value: Any) -> Optional[str]:
        """
        Normalize date to YYYY-MM-DD format
        
        Args:
            value: Date value (string, datetime, date)
            
        Returns:
            ISO format string (YYYY-MM-DD) or None if invalid
        """
        if not value:
            return None
        
        try:
            # Already a date object
            if isinstance(value, date):
                return value.strftime(InvoiceNormalizationService.DATE_FORMAT)
            
            # Datetime object
            if isinstance(value, datetime):
                return value.strftime(InvoiceNormalizationService.DATE_FORMAT)
            
            # String - try to parse
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    return None
                
                # Try common formats
                formats = [
                    '%Y-%m-%d',           # 2024-03-15
                    '%d/%m/%Y',           # 15/03/2024
                    '%m/%d/%Y',           # 03/15/2024
                    '%d-%m-%Y',           # 15-03-2024
                    '%Y/%m/%d',           # 2024/03/15
                    '%d.%m.%Y',           # 15.03.2024
                    '%B %d, %Y',          # March 15, 2024
                    '%b %d, %Y',          # Mar 15, 2024
                    '%d %B %Y',           # 15 March 2024
                    '%d %b %Y',           # 15 Mar 2024
                    '%Y%m%d',             # 20240315
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime(InvoiceNormalizationService.DATE_FORMAT)
                    except ValueError:
                        continue
                
                logger.warning(f"Could not parse date: {value}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error normalizing date '{value}': {e}")
            return None
    
    @staticmethod
    def normalize_amount(value: Any) -> Optional[Decimal]:
        """
        Normalize amount to Decimal type
        
        Args:
            value: Amount value (string, int, float, Decimal)
            
        Returns:
            Decimal or None if invalid
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        
        try:
            # Already Decimal
            if isinstance(value, Decimal):
                return value
            
            # String - clean and parse
            if isinstance(value, str):
                # Remove common currency symbols and formatting
                cleaned = value.strip()
                cleaned = re.sub(r'[^\d.,\-]', '', cleaned)
                cleaned = cleaned.replace(',', '')  # Remove thousands separator
                cleaned = cleaned.replace(' ', '')
                
                if not cleaned:
                    return None
                
                return Decimal(cleaned)
            
            # Numeric types
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            
            return None
            
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Could not parse amount '{value}': {e}")
            return None
    
    @staticmethod
    def normalize_currency(value: Any) -> Optional[str]:
        """
        Normalize currency code to ISO 4217 format
        
        Args:
            value: Currency value (code or symbol)
            
        Returns:
            ISO 4217 currency code or None
        """
        if not value:
            return None
        
        try:
            if isinstance(value, str):
                # Clean and normalize
                cleaned = value.strip().lower()
                
                if not cleaned:
                    return None
                
                # Check if it's in the map
                if cleaned in InvoiceNormalizationService.CURRENCY_MAP:
                    return InvoiceNormalizationService.CURRENCY_MAP[cleaned]
                
                # Check if it's already a valid 3-letter code
                if len(cleaned) == 3 and cleaned.isalpha():
                    return cleaned.upper()
                
                # Try to map first word
                first_word = cleaned.split()[0]
                if first_word in InvoiceNormalizationService.CURRENCY_MAP:
                    return InvoiceNormalizationService.CURRENCY_MAP[first_word]
                
                logger.warning(f"Unknown currency: {value}")
                return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error normalizing currency '{value}': {e}")
            return None
    
    @staticmethod
    def normalize_string(value: Any, max_length: Optional[int] = None) -> Optional[str]:
        """
        Normalize string value
        
        Args:
            value: String value
            max_length: Optional max length
            
        Returns:
            Normalized string or None
        """
        if not value:
            return None
        
        try:
            if isinstance(value, str):
                cleaned = value.strip()
                if not cleaned:
                    return None
                
                if max_length:
                    cleaned = cleaned[:max_length]
                
                return cleaned
            
            return None
            
        except Exception as e:
            logger.warning(f"Error normalizing string '{value}': {e}")
            return None
    
    @staticmethod
    def normalize_invoice_item(item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a single invoice line item
        
        Args:
            item: Item dict with product, quantity, unit_price, total, etc.
            
        Returns:
            Normalized item dict
        """
        if not isinstance(item, dict):
            return {}
        
        normalized = {
            'product': InvoiceNormalizationService.normalize_string(
                item.get('product')
            ),
            'description': InvoiceNormalizationService.normalize_string(
                item.get('description')
            ),
            'quantity': InvoiceNormalizationService.normalize_amount(
                item.get('quantity')
            ),
            'unit_price': InvoiceNormalizationService.normalize_amount(
                item.get('unit_price')
            ),
            'discount': InvoiceNormalizationService.normalize_amount(
                item.get('discount')
            ) or Decimal('0'),
            'total': InvoiceNormalizationService.normalize_amount(
                item.get('total')
            ),
        }
        
        # Convert Decimal to string for JSON serialization
        for key in ['quantity', 'unit_price', 'discount', 'total']:
            if normalized[key] is not None:
                normalized[key] = str(normalized[key])
        
        return normalized
    
    @staticmethod
    def normalize_invoice_json(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize full extracted invoice data
        
        Args:
            extracted_data: Raw extracted invoice JSON from OpenAI
            
        Returns:
            Normalized invoice data
        """
        if not isinstance(extracted_data, dict):
            return {}
        
        normalized = {
            'invoice_number': InvoiceNormalizationService.normalize_string(
                extracted_data.get('invoice_number'), max_length=100
            ),
            'issue_date': InvoiceNormalizationService.normalize_date(
                extracted_data.get('issue_date')
            ),
            'due_date': InvoiceNormalizationService.normalize_date(
                extracted_data.get('due_date')
            ),
            'vendor': {
                'name': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('vendor', {}).get('name'), max_length=255
                ),
                'address': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('vendor', {}).get('address'), max_length=500
                ),
                'city': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('vendor', {}).get('city'), max_length=100
                ),
                'country': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('vendor', {}).get('country'), max_length=100
                ),
            },
            'customer': {
                'name': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('customer', {}).get('name'), max_length=255
                ),
                'address': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('customer', {}).get('address'), max_length=500
                ),
                'city': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('customer', {}).get('city'), max_length=100
                ),
                'country': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('customer', {}).get('country'), max_length=100
                ),
                'tin': InvoiceNormalizationService.normalize_string(
                    extracted_data.get('customer', {}).get('tin'), max_length=50
                ),
            },
            'items': [],
            'total_amount': InvoiceNormalizationService.normalize_amount(
                extracted_data.get('total_amount')
            ),
            'currency': InvoiceNormalizationService.normalize_currency(
                extracted_data.get('currency')
            ) or 'USD',  # Default to USD
        }
        
        # Normalize items
        items = extracted_data.get('items', [])
        if isinstance(items, list):
            for item in items:
                normalized_item = InvoiceNormalizationService.normalize_invoice_item(item)
                if normalized_item.get('product') or normalized_item.get('description'):
                    normalized['items'].append(normalized_item)
        
        # Convert Decimal to string for JSON
        if normalized['total_amount'] is not None:
            normalized['total_amount'] = str(normalized['total_amount'])
        
        return normalized


# Singleton instance
invoice_normalization_service = InvoiceNormalizationService()
