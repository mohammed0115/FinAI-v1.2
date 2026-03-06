"""
Invoice Validation Service - Phase 2

This service validates extracted invoice data:
- Required fields exist
- Business rules compliance
- Data consistency checks
Returns errors and warnings for review
"""

import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


class ValidationMessage:
    """Container for validation error/warning"""
    
    def __init__(self, level: str, code: str, message: str, field: str = None):
        self.level = level  # 'error' or 'warning'
        self.code = code    # Machine-readable code
        self.message = message  # Human-readable message
        self.field = field  # Field that caused the issue
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary"""
        return {
            'level': self.level,
            'code': self.code,
            'message': self.message,
            'field': self.field
        }


class InvoiceValidationService:
    """
    Validate extracted and normalized invoice data
    """
    
    @staticmethod
    def validate_invoice(
        normalized_data: Dict[str, Any]
    ) -> Tuple[bool, List[ValidationMessage]]:
        """
        Validate complete invoice data
        
        Args:
            normalized_data: Normalized invoice dict from normalization service
            
        Returns:
            Tuple of (is_valid: bool, messages: List[ValidationMessage])
        """
        messages: List[ValidationMessage] = []
        
        # Required field validations
        messages.extend(InvoiceValidationService._validate_required_fields(normalized_data))
        
        # Business rule validations
        messages.extend(InvoiceValidationService._validate_business_rules(normalized_data))
        
        # Data consistency validations
        messages.extend(InvoiceValidationService._validate_consistency(normalized_data))
        
        # Determine if valid (has no errors, only warnings are OK)
        has_errors = any(m.level == 'error' for m in messages)
        is_valid = not has_errors
        
        return is_valid, messages
    
    @staticmethod
    def _validate_required_fields(data: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate that required fields exist and have values"""
        messages = []
        
        # Invoice number is required
        if not data.get('invoice_number'):
            messages.append(ValidationMessage(
                level='error',
                code='MISSING_INVOICE_NUMBER',
                message='Invoice number is required',
                field='invoice_number'
            ))
        
        # Issue date is required
        if not data.get('issue_date'):
            messages.append(ValidationMessage(
                level='error',
                code='MISSING_ISSUE_DATE',
                message='Issue date is required',
                field='issue_date'
            ))
        
        # Vendor name is required
        vendor_name = data.get('vendor', {}).get('name')
        if not vendor_name:
            messages.append(ValidationMessage(
                level='error',
                code='MISSING_VENDOR_NAME',
                message='Vendor name is required',
                field='vendor.name'
            ))
        
        # At least one item is required
        items = data.get('items', [])
        if not items or len(items) == 0:
            messages.append(ValidationMessage(
                level='error',
                code='MISSING_ITEMS',
                message='At least one line item is required',
                field='items'
            ))
        
        # Total amount is required
        if not data.get('total_amount'):
            messages.append(ValidationMessage(
                level='error',
                code='MISSING_TOTAL_AMOUNT',
                message='Total amount is required',
                field='total_amount'
            ))
        
        return messages
    
    @staticmethod
    def _validate_business_rules(data: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate business rules"""
        messages = []
        
        # Date logic: issue_date must be before or equal to due_date
        issue_date = data.get('issue_date')
        due_date = data.get('due_date')
        
        if issue_date and due_date:
            try:
                # Parse dates if they're strings
                if isinstance(issue_date, str):
                    issue_dt = datetime.strptime(issue_date, '%Y-%m-%d')
                else:
                    issue_dt = issue_date
                
                if isinstance(due_date, str):
                    due_dt = datetime.strptime(due_date, '%Y-%m-%d')
                else:
                    due_dt = due_date
                
                if issue_dt > due_dt:
                    messages.append(ValidationMessage(
                        level='error',
                        code='INVALID_DATE_RANGE',
                        message='Issue date must be before or equal to due date',
                        field='due_date'
                    ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not compare dates: {e}")
        
        # Warn if due_date is missing but issue_date exists
        if issue_date and not due_date:
            messages.append(ValidationMessage(
                level='warning',
                code='MISSING_DUE_DATE',
                message='Due date is not specified',
                field='due_date'
            ))
        
        # Currency validation
        currency = data.get('currency')
        if currency and len(currency) != 3:
            messages.append(ValidationMessage(
                level='warning',
                code='INVALID_CURRENCY_FORMAT',
                message=f'Currency code should be 3 characters (ISO 4217), got: {currency}',
                field='currency'
            ))
        
        return messages
    
    @staticmethod
    def _validate_consistency(data: Dict[str, Any]) -> List[ValidationMessage]:
        """Validate data consistency (line totals, amounts, etc.)"""
        messages = []
        
        items = data.get('items', [])
        
        # Validate each item
        for idx, item in enumerate(items, 1):
            item_messages = InvoiceValidationService._validate_item(item, idx)
            messages.extend(item_messages)
        
        # Validate line totals sum to invoice total
        if items and data.get('total_amount'):
            calculated_total = InvoiceValidationService._calculate_line_totals(items)
            invoice_total = InvoiceValidationService._parse_decimal(data.get('total_amount'))
            
            if calculated_total is not None and invoice_total is not None:
                # Allow small rounding differences (0.01)
                difference = abs(calculated_total - invoice_total)
                
                if difference > Decimal('0.01'):
                    messages.append(ValidationMessage(
                        level='warning',
                        code='TOTAL_MISMATCH',
                        message=f'Sum of line totals ({calculated_total}) does not match invoice total ({invoice_total}). Difference: {difference}',
                        field='total_amount'
                    ))
        
        return messages
    
    @staticmethod
    def _validate_item(item: Dict[str, Any], index: int) -> List[ValidationMessage]:
        """Validate a single line item"""
        messages = []
        
        # Each item should have product or description
        product = item.get('product')
        description = item.get('description')
        
        if not product and not description:
            messages.append(ValidationMessage(
                level='warning',
                code='ITEM_NO_DESCRIPTION',
                message=f'Line item {index} has no product or description',
                field=f'items[{index}]'
            ))
        
        # Quantity validation
        quantity = InvoiceValidationService._parse_decimal(item.get('quantity'))
        unit_price = InvoiceValidationService._parse_decimal(item.get('unit_price'))
        total = InvoiceValidationService._parse_decimal(item.get('total'))
        
        if quantity is not None and quantity <= 0:
            messages.append(ValidationMessage(
                level='warning',
                code='INVALID_QUANTITY',
                message=f'Line item {index}: quantity must be positive',
                field=f'items[{index}].quantity'
            ))
        
        if unit_price is not None and unit_price < 0:
            messages.append(ValidationMessage(
                level='warning',
                code='INVALID_UNIT_PRICE',
                message=f'Line item {index}: unit price must be non-negative',
                field=f'items[{index}].unit_price'
            ))
        
        # Validate line total = quantity * unit_price
        if quantity is not None and unit_price is not None and total is not None:
            discount = InvoiceValidationService._parse_decimal(item.get('discount')) or Decimal('0')
            calculated_total = (quantity * unit_price) - discount
            
            # Allow small rounding differences
            if abs(calculated_total - total) > Decimal('0.01'):
                messages.append(ValidationMessage(
                    level='warning',
                    code='ITEM_TOTAL_MISMATCH',
                    message=f'Line item {index}: calculated total ({calculated_total}) does not match stated total ({total})',
                    field=f'items[{index}].total'
                ))
        
        return messages
    
    @staticmethod
    def _calculate_line_totals(items: List[Dict[str, Any]]) -> Decimal:
        """Calculate sum of all line item totals"""
        total = Decimal('0')
        
        for item in items:
            item_total = InvoiceValidationService._parse_decimal(item.get('total'))
            if item_total is not None:
                total += item_total
        
        return total
    
    @staticmethod
    def _parse_decimal(value: Any) -> Decimal:
        """Parse value to Decimal, return None if invalid"""
        if value is None:
            return None
        
        try:
            if isinstance(value, Decimal):
                return value
            
            if isinstance(value, str):
                return Decimal(value)
            
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            
            return None
        except:
            return None


def get_validation_summary(messages: List[ValidationMessage]) -> Dict[str, Any]:
    """Get summary of validation results"""
    errors = [m for m in messages if m.level == 'error']
    warnings = [m for m in messages if m.level == 'warning']
    
    return {
        'is_valid': len(errors) == 0,
        'error_count': len(errors),
        'warning_count': len(warnings),
        'total_issues': len(messages),
        'errors': [m.to_dict() for m in errors],
        'warnings': [m.to_dict() for m in warnings],
    }


# Singleton instance
invoice_validation_service = InvoiceValidationService()
