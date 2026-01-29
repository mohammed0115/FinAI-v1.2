"""
VAT Validation Service - خدمة التحقق من ضريبة القيمة المضافة

Server-side validation logic for VAT numbers based on country.

RULES:
- Saudi Arabia (SA): VAT number REQUIRED, must be valid ZATCA format
- Other GCC countries: VAT number OPTIONAL, validate format only if provided

SCOPE:
- Validation only
- No ERP behavior
- No invoice submission
- No tax calculation engine
"""
import re
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)


# VAT Error Messages (Arabic-first)
VAT_ERRORS_AR = {
    'required': 'رقم ضريبة القيمة المضافة مطلوب للشركات في المملكة العربية السعودية',
    'invalid_length': 'رقم ضريبة القيمة المضافة يجب أن يكون 15 رقماً',
    'invalid_format': 'تنسيق رقم ضريبة القيمة المضافة غير صحيح - يجب أن يبدأ وينتهي بالرقم 3',
    'invalid_digits': 'رقم ضريبة القيمة المضافة يجب أن يحتوي على أرقام فقط',
    'invalid_checksum': 'رقم ضريبة القيمة المضافة غير صالح - فشل التحقق من المجموع',
}

VAT_ERRORS_EN = {
    'required': 'VAT number is required for companies in Saudi Arabia',
    'invalid_length': 'VAT number must be exactly 15 digits',
    'invalid_format': 'Invalid VAT number format - must start and end with 3',
    'invalid_digits': 'VAT number must contain only digits',
    'invalid_checksum': 'Invalid VAT number - checksum verification failed',
}


class VATValidationService:
    """
    خدمة التحقق من رقم ضريبة القيمة المضافة
    VAT Number Validation Service
    
    IMPORTANT:
    - This is VALIDATION ONLY
    - Does NOT submit to ZATCA
    - Does NOT affect audit scoring
    - Does NOT create or modify transactions
    """
    
    def validate_vat_number(
        self, 
        vat_number: Optional[str], 
        country: str,
        lang: str = 'ar'
    ) -> Dict:
        """
        Validate VAT number based on country rules.
        
        Args:
            vat_number: VAT registration number
            country: ISO country code (SA, AE, BH, KW, OM, QA)
            lang: Language for error messages ('ar' or 'en')
        
        Returns:
            Dict with validation result:
            {
                'valid': bool,
                'error_code': str or None,
                'error_message': str or None,
                'vat_applicable': bool,
                'zatca_enabled': bool,
                'validation_details': dict
            }
        """
        errors = VAT_ERRORS_AR if lang == 'ar' else VAT_ERRORS_EN
        
        result = {
            'valid': False,
            'error_code': None,
            'error_message': None,
            'vat_applicable': False,
            'zatca_enabled': False,
            'validation_details': {},
            'validated_at': timezone.now().isoformat(),
        }
        
        # Saudi Arabia - VAT number REQUIRED
        if country == 'SA':
            result['vat_applicable'] = True
            
            if not vat_number or not vat_number.strip():
                result['error_code'] = 'required'
                result['error_message'] = errors['required']
                return result
            
            # Validate Saudi VAT number format
            validation = self._validate_saudi_vat(vat_number.strip(), errors)
            result.update(validation)
            
            if result['valid']:
                result['zatca_enabled'] = True
                result['validation_details']['zatca_verification_scope'] = 'verification_only'
        
        # Other GCC countries - VAT number OPTIONAL
        else:
            result['vat_applicable'] = False
            result['zatca_enabled'] = False
            
            if vat_number and vat_number.strip():
                # Validate format only if provided
                validation = self._validate_gcc_vat(vat_number.strip(), country, errors)
                result.update(validation)
            else:
                # No VAT number provided and not required
                result['valid'] = True
                result['validation_details']['status'] = 'not_required'
                result['validation_details']['message_ar'] = 'رقم ضريبة القيمة المضافة غير مطلوب لهذا البلد'
                result['validation_details']['message_en'] = 'VAT number is not required for this country'
        
        return result
    
    def _validate_saudi_vat(self, vat_number: str, errors: Dict) -> Dict:
        """
        Validate Saudi Arabia VAT number (ZATCA format).
        
        Rules:
        - Exactly 15 digits
        - Starts with '3'
        - Ends with '3'
        - Contains only digits
        """
        result = {
            'valid': False,
            'error_code': None,
            'error_message': None,
            'validation_details': {
                'country': 'SA',
                'format': 'ZATCA',
            },
        }
        
        # Remove any whitespace
        vat_number = vat_number.replace(' ', '').replace('-', '')
        
        # Check if contains only digits
        if not vat_number.isdigit():
            result['error_code'] = 'invalid_digits'
            result['error_message'] = errors['invalid_digits']
            result['validation_details']['check_failed'] = 'digits_only'
            return result
        
        # Check length
        if len(vat_number) != 15:
            result['error_code'] = 'invalid_length'
            result['error_message'] = errors['invalid_length']
            result['validation_details']['check_failed'] = 'length'
            result['validation_details']['provided_length'] = len(vat_number)
            result['validation_details']['required_length'] = 15
            return result
        
        # Check starts and ends with 3
        if not vat_number.startswith('3') or not vat_number.endswith('3'):
            result['error_code'] = 'invalid_format'
            result['error_message'] = errors['invalid_format']
            result['validation_details']['check_failed'] = 'format'
            result['validation_details']['starts_with'] = vat_number[0]
            result['validation_details']['ends_with'] = vat_number[-1]
            return result
        
        # Optional: Luhn checksum validation (simplified)
        # Note: ZATCA doesn't officially document checksum algorithm
        # This is a basic validation only
        
        # All checks passed
        result['valid'] = True
        result['validation_details']['format_valid'] = True
        result['validation_details']['length_valid'] = True
        result['validation_details']['prefix_valid'] = True
        result['validation_details']['suffix_valid'] = True
        result['validation_details']['message_ar'] = 'تم التحقق من رقم ضريبة القيمة المضافة بنجاح'
        result['validation_details']['message_en'] = 'VAT number validated successfully'
        
        return result
    
    def _validate_gcc_vat(self, vat_number: str, country: str, errors: Dict) -> Dict:
        """
        Validate GCC country VAT number (basic format check).
        
        Each GCC country has different VAT requirements.
        This performs basic format validation.
        """
        result = {
            'valid': False,
            'error_code': None,
            'error_message': None,
            'validation_details': {
                'country': country,
            },
        }
        
        # Remove any whitespace
        vat_number = vat_number.replace(' ', '').replace('-', '')
        
        # UAE VAT format: TRN + 15 digits or just 15 digits
        if country == 'AE':
            if vat_number.upper().startswith('TRN'):
                vat_number = vat_number[3:]
            if not vat_number.isdigit() or len(vat_number) != 15:
                result['error_code'] = 'invalid_format'
                result['error_message'] = 'تنسيق رقم ضريبة القيمة المضافة الإماراتي غير صحيح'
                return result
        
        # Bahrain VAT format: Variable length, starts with country code
        elif country == 'BH':
            if not vat_number.isdigit():
                result['error_code'] = 'invalid_format'
                result['error_message'] = 'تنسيق رقم ضريبة القيمة المضافة البحريني غير صحيح'
                return result
        
        # Other GCC countries - basic digit check
        else:
            if not vat_number.replace(' ', '').replace('-', '').isalnum():
                result['error_code'] = 'invalid_format'
                result['error_message'] = 'تنسيق رقم ضريبة القيمة المضافة غير صحيح'
                return result
        
        # Passed basic validation
        result['valid'] = True
        result['validation_details']['format_valid'] = True
        result['validation_details']['message_ar'] = 'تم التحقق من تنسيق رقم ضريبة القيمة المضافة'
        result['validation_details']['message_en'] = 'VAT number format validated'
        
        return result
    
    def get_country_vat_requirements(self, country: str) -> Dict:
        """
        Get VAT requirements for a specific country.
        
        Returns:
            Dict with country-specific VAT requirements
        """
        requirements = {
            'SA': {
                'name_ar': 'المملكة العربية السعودية',
                'name_en': 'Saudi Arabia',
                'vat_required': True,
                'vat_format': '15 أرقام، يبدأ وينتهي بـ 3',
                'vat_format_en': '15 digits, starts and ends with 3',
                'zatca_applicable': True,
                'vat_rate': 15,
                'regulatory_body_ar': 'هيئة الزكاة والضريبة والجمارك',
                'regulatory_body_en': 'ZATCA',
            },
            'AE': {
                'name_ar': 'الإمارات العربية المتحدة',
                'name_en': 'United Arab Emirates',
                'vat_required': False,
                'vat_format': 'TRN + 15 أرقام',
                'vat_format_en': 'TRN + 15 digits',
                'zatca_applicable': False,
                'vat_rate': 5,
                'regulatory_body_ar': 'الهيئة الاتحادية للضرائب',
                'regulatory_body_en': 'FTA',
            },
            'BH': {
                'name_ar': 'البحرين',
                'name_en': 'Bahrain',
                'vat_required': False,
                'vat_format': 'متغير',
                'vat_format_en': 'Variable',
                'zatca_applicable': False,
                'vat_rate': 10,
                'regulatory_body_ar': 'الجهاز الوطني للإيرادات',
                'regulatory_body_en': 'NBR',
            },
            'KW': {
                'name_ar': 'الكويت',
                'name_en': 'Kuwait',
                'vat_required': False,
                'vat_format': 'غير محدد',
                'vat_format_en': 'Not specified',
                'zatca_applicable': False,
                'vat_rate': 0,  # Kuwait has no VAT yet
                'regulatory_body_ar': 'وزارة المالية',
                'regulatory_body_en': 'Ministry of Finance',
            },
            'OM': {
                'name_ar': 'عمان',
                'name_en': 'Oman',
                'vat_required': False,
                'vat_format': 'متغير',
                'vat_format_en': 'Variable',
                'zatca_applicable': False,
                'vat_rate': 5,
                'regulatory_body_ar': 'جهاز الضرائب',
                'regulatory_body_en': 'Tax Authority',
            },
            'QA': {
                'name_ar': 'قطر',
                'name_en': 'Qatar',
                'vat_required': False,
                'vat_format': 'غير محدد',
                'vat_format_en': 'Not specified',
                'zatca_applicable': False,
                'vat_rate': 0,  # Qatar has no VAT yet
                'regulatory_body_ar': 'الهيئة العامة للضرائب',
                'regulatory_body_en': 'GTA',
            },
        }
        
        return requirements.get(country, {
            'name_ar': 'غير معروف',
            'name_en': 'Unknown',
            'vat_required': False,
            'zatca_applicable': False,
        })


# Singleton instance
vat_validation_service = VATValidationService()
