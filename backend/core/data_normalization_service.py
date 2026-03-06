"""
Data Normalization & Validation Service - Phase 2
خدمة تطبيع والتحقق من البيانات

Normalizes extracted invoice data and performs comprehensive validation checks.

Normalizations:
- Dates to YYYY-MM-DD format
- Numbers to Decimal
- Currency codes normalization
- Clean null/empty fields

Validations:
- Invoice number exists
- Vendor name exists
- Items exist
- Totals match calculations
- Dates are valid and logical
"""

import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class DataNormalizationValidator:
    """Service for normalizing and validating extracted invoice data"""
    
    # Standard currency codes
    VALID_CURRENCIES = {
        'SAR', 'AED', 'KWD', 'BHD', 'OMR', 'QAR', 'USD', 'EUR',
        'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'INR'
    }
    
    CURRENCY_DEFAULTS = {
        'sa': 'SAR',
        'saudi': 'SAR',
        'uae': 'AED',
        'kuwait': 'KWD',
        'bahrain': 'BHD',
        'oman': 'OMR',
        'qatar': 'QAR',
    }
    
    @staticmethod
    def normalize_date(date_value: Any) -> Tuple[str, bool]:
        """
        Normalize date to YYYY-MM-DD format
        
        Returns:
            Tuple of (normalized_date_string, is_valid)
        """
        if not date_value:
            return None, False
        
        if isinstance(date_value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d',
                '%d-%m-%Y',
                '%m-%d-%Y',
                '%Y/%m/%d',
                '%d/%m/%Y',
                '%m/%d/%Y',
                '%d.%m.%Y',
                '%Y.%m.%d',
                '%B %d, %Y',
                '%d %B %Y',
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_value.strip(), fmt)
                    return parsed_date.strftime('%Y-%m-%d'), True
                except ValueError:
                    continue
        
        elif isinstance(date_value, datetime):
            return date_value.strftime('%Y-%m-%d'), True
        
        logger.warning(f"Could not normalize date: {date_value}")
        return None, False
    
    @staticmethod
    def normalize_decimal(value: Any) -> Tuple[Decimal, bool]:
        """
        Normalize value to Decimal for financial precision
        
        Returns:
            Tuple of (decimal_value, is_valid)
        """
        if value is None or value == '':
            return None, False
        
        try:
            # Handle string with currency symbols
            if isinstance(value, str):
                # Remove common currency symbols
                cleaned = re.sub(r'[\$€£¥₹ريال دينار درهم]', '', value)
                # Remove commas and spaces
                cleaned = cleaned.replace(',', '').replace(' ', '').strip()
                # Handle both . and , as decimal separator
                if ',' in cleaned and '.' not in cleaned:
                    cleaned = cleaned.replace(',', '.')
                
                value = cleaned
            
            decimal_value = Decimal(str(value))
            
            # Ensure reasonable financial value (not too large or too small)
            if abs(decimal_value) > Decimal('999999999.99'):
                logger.warning(f"Decimal value too large: {decimal_value}")
                return None, False
            
            return decimal_value, True
            
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(f"Could not normalize decimal: {value} - {e}")
            return None, False
    
    @staticmethod
    def normalize_currency(currency: str) -> Tuple[str, bool]:
        """
        Normalize currency code
        
        Returns:
            Tuple of (currency_code, is_valid)
        """
        if not currency:
            return 'SAR', False  # Default to SAR but mark as invalid
        
        currency = str(currency).upper().strip()
        
        # Direct match
        if currency in DataNormalizationValidator.VALID_CURRENCIES:
            return currency, True
        
        # Try to map common variations
        currency_lower = currency.lower()
        if currency_lower in DataNormalizationValidator.CURRENCY_DEFAULTS:
            mapped = DataNormalizationValidator.CURRENCY_DEFAULTS[currency_lower]
            return mapped, True
        
        # Try to extract currency code from longer strings
        match = re.search(r'\b([A-Z]{3})\b', currency)
        if match:
            code = match.group(1)
            if code in DataNormalizationValidator.VALID_CURRENCIES:
                return code, True
        
        logger.warning(f"Could not normalize currency: {currency}")
        return currency.upper() if len(currency) <= 3 else 'SAR', False
    
    @staticmethod
    def clean_string(value: str) -> str:
        """Clean and normalize string values"""
        if not value:
            return None
        
        value = str(value).strip()
        # Remove extra whitespace
        value = ' '.join(value.split())
        return value if value else None
    
    @staticmethod
    def normalize_invoice_data(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize all extracted invoice data
        
        Args:
            extracted_data: Raw extracted data from OpenAI
        
        Returns:
            Normalized data dictionary
        """
        normalized = {}
        
        # Invoice number
        normalized['invoice_number'] = DataNormalizationValidator.clean_string(
            extracted_data.get('invoice_number')
        )
        
        # Dates
        issue_date, _ = DataNormalizationValidator.normalize_date(
            extracted_data.get('issue_date')
        )
        normalized['issue_date'] = issue_date
        
        due_date, _ = DataNormalizationValidator.normalize_date(
            extracted_data.get('due_date')
        )
        normalized['due_date'] = due_date
        
        # Names
        normalized['vendor_name'] = DataNormalizationValidator.clean_string(
            extracted_data.get('vendor_name')
        )
        normalized['customer_name'] = DataNormalizationValidator.clean_string(
            extracted_data.get('customer_name')
        )
        normalized['vendor_tax_id'] = DataNormalizationValidator.clean_string(
            extracted_data.get('vendor_tax_id')
        )
        normalized['customer_tax_id'] = DataNormalizationValidator.clean_string(
            extracted_data.get('customer_tax_id')
        )
        
        # Amounts
        subtotal, _ = DataNormalizationValidator.normalize_decimal(
            extracted_data.get('subtotal')
        )
        normalized['subtotal'] = subtotal
        
        tax_amount, _ = DataNormalizationValidator.normalize_decimal(
            extracted_data.get('tax_amount')
        )
        normalized['tax_amount'] = tax_amount
        
        total_amount, _ = DataNormalizationValidator.normalize_decimal(
            extracted_data.get('total_amount')
        )
        normalized['total_amount'] = total_amount
        
        discount_amount, _ = DataNormalizationValidator.normalize_decimal(
            extracted_data.get('discount_amount')
        )
        normalized['discount_amount'] = discount_amount
        
        # Tax rate
        tax_rate, _ = DataNormalizationValidator.normalize_decimal(
            extracted_data.get('tax_rate')
        )
        normalized['tax_rate'] = tax_rate
        
        # Currency
        currency, _ = DataNormalizationValidator.normalize_currency(
            extracted_data.get('currency')
        )
        normalized['currency'] = currency
        
        # Items
        items = extracted_data.get('items', [])
        normalized['items'] = DataNormalizationValidator._normalize_items(items)
        
        # Preserve other fields
        normalized['extraction_engine'] = extracted_data.get('extraction_engine')
        normalized['confidence'] = extracted_data.get('confidence', 0)
        normalized['language_detected'] = extracted_data.get('language_detected', 'unknown')
        
        return normalized
    
    @staticmethod
    def _normalize_items(items: List[Dict]) -> List[Dict]:
        """Normalize line items"""
        normalized_items = []
        
        for item in items:
            if not isinstance(item, dict):
                continue
            
            normalized_item = {
                'description': DataNormalizationValidator.clean_string(
                    item.get('description')
                ),
                'quantity': None,
                'unit_price': None,
                'line_total': None,
            }
            
            quantity, _ = DataNormalizationValidator.normalize_decimal(
                item.get('quantity')
            )
            normalized_item['quantity'] = quantity
            
            unit_price, _ = DataNormalizationValidator.normalize_decimal(
                item.get('unit_price')
            )
            normalized_item['unit_price'] = unit_price
            
            line_total, _ = DataNormalizationValidator.normalize_decimal(
                item.get('line_total')
            )
            normalized_item['line_total'] = line_total
            
            normalized_items.append(normalized_item)
        
        return normalized_items
    
    @staticmethod
    def validate_invoice_data(normalized_data: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """
        Validate normalized invoice data
        
        Args:
            normalized_data: Normalized invoice data
        
        Returns:
            Tuple of (is_valid, errors_list, warnings_list)
        """
        errors = []
        warnings = []
        
        # Required field checks
        if not normalized_data.get('invoice_number'):
            errors.append("Invoice number is required")
        
        if not normalized_data.get('vendor_name'):
            errors.append("Vendor name is required")
        
        if not normalized_data.get('total_amount'):
            errors.append("Total amount is required")
        
        # Date validations
        if normalized_data.get('issue_date'):
            if normalized_data.get('due_date'):
                try:
                    issue = datetime.strptime(normalized_data['issue_date'], '%Y-%m-%d')
                    due = datetime.strptime(normalized_data['due_date'], '%Y-%m-%d')
                    
                    if due < issue:
                        errors.append("Due date must be after or equal to issue date")
                except ValueError:
                    warnings.append("Could not validate date order")
        
        # Items validation
        items = normalized_data.get('items', [])
        if not items:
            warnings.append("No line items found")
        
        # Totals validation
        if items:
            items_total = Decimal('0')
            for item in items:
                if item.get('line_total'):
                    items_total += item['line_total']
            
            if normalized_data.get('subtotal'):
                if abs(items_total - normalized_data['subtotal']) > Decimal('0.01'):
                    warnings.append(
                        f"Subtotal mismatch: Items total {items_total} != "
                        f"Subtotal {normalized_data['subtotal']}"
                    )
            
            if normalized_data.get('total_amount'):
                # Check if total matches subtotal + tax - discount
                calc_total = items_total
                if normalized_data.get('tax_amount'):
                    calc_total += normalized_data['tax_amount']
                if normalized_data.get('discount_amount'):
                    calc_total -= normalized_data['discount_amount']
                
                if abs(calc_total - normalized_data['total_amount']) > Decimal('0.01'):
                    warnings.append(
                        f"Total mismatch: Calculated {calc_total} != "
                        f"Invoice total {normalized_data['total_amount']}"
                    )
        
        # Currency validation
        if normalized_data.get('currency') not in DataNormalizationValidator.VALID_CURRENCIES:
            warnings.append(f"Unrecognized currency: {normalized_data.get('currency')}")
        
        is_valid = len(errors) == 0
        
        return is_valid, errors, warnings


def get_normalization_validator() -> DataNormalizationValidator:
    """Get normalization validator (stateless, can be instantiated fresh)"""
    return DataNormalizationValidator()
