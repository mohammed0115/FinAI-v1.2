"""
Settings Views - وجهات الإعدادات
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
import logging

from core.models import Organization
from core.vat_validation_service import vat_validation_service

logger = logging.getLogger(__name__)


@require_POST
def toggle_language_view(request):
    """
    Toggle between Arabic and English UI language.
    
    NOTE: This is UI-level only. Audit logic remains unchanged.
    Arabic is the primary language.
    """
    current_lang = request.session.get('language', 'ar')
    new_lang = 'en' if current_lang == 'ar' else 'ar'
    request.session['language'] = new_lang
    
    # Get the referring page or default to dashboard
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)


@login_required
def organization_settings_view(request):
    """
    إعدادات الشركة / المنظمة
    Company / Organization Settings
    
    VAT HANDLING LOGIC:
    - Saudi Arabia (SA): VAT number REQUIRED, validated against ZATCA format
    - Other GCC countries: VAT number OPTIONAL
    - Validation only - no ERP behavior
    """
    user = request.user
    organization = user.organization
    
    if not organization:
        messages.error(request, 'لا توجد شركة مرتبطة بحسابك')
        return redirect('dashboard')
    
    vat_requirements = vat_validation_service.get_country_vat_requirements(organization.country)
    validation_result = None
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        country = request.POST.get('country', organization.country)
        vat_number = request.POST.get('vat_number', '').strip()
        company_type = request.POST.get('company_type', '')
        industry = request.POST.get('industry', '').strip()
        
        # Get language for error messages
        lang = request.session.get('language', 'ar')
        
        # Validate VAT number
        validation_result = vat_validation_service.validate_vat_number(
            vat_number=vat_number,
            country=country,
            lang=lang
        )
        
        if validation_result['valid']:
            # Update organization
            organization.name = name or organization.name
            organization.name_ar = name_ar
            organization.country = country
            organization.vat_number = vat_number if vat_number else None
            organization.vat_applicable = validation_result['vat_applicable']
            organization.zatca_enabled = validation_result['zatca_enabled']
            organization.company_type = company_type or None
            organization.industry = industry or None
            
            # Update VAT validation status
            if vat_number:
                organization.vat_validation_status = 'valid'
                organization.vat_validation_message = validation_result['validation_details'].get('message_ar', '')
            elif country == 'SA':
                organization.vat_validation_status = 'invalid'
                organization.vat_validation_message = 'رقم ضريبة القيمة المضافة مطلوب'
            else:
                organization.vat_validation_status = 'not_required'
                organization.vat_validation_message = 'رقم ضريبة القيمة المضافة غير مطلوب لهذا البلد'
            
            organization.vat_validated_at = timezone.now()
            
            # Update ZATCA scope based on VAT validation
            if organization.zatca_enabled:
                organization.zatca_verification_scope = 'verification_only'
            else:
                organization.zatca_verification_scope = 'disabled'
            
            organization.save()
            
            messages.success(request, 'تم حفظ إعدادات الشركة بنجاح')
            logger.info(f"Organization settings updated: {organization.name} by {user.email}")
            
            return redirect('organization_settings')
        else:
            # Validation failed - show error
            messages.error(request, validation_result['error_message'])
    
    # Get all country requirements for UI
    all_country_requirements = {
        code: vat_validation_service.get_country_vat_requirements(code)
        for code, _ in Organization.COUNTRY_CHOICES
    }
    
    context = {
        'organization': organization,
        'vat_requirements': vat_requirements,
        'all_country_requirements': all_country_requirements,
        'validation_result': validation_result,
        'country_choices': Organization.COUNTRY_CHOICES,
        'company_type_choices': Organization.COMPANY_TYPE_CHOICES,
    }
    
    return render(request, 'settings/organization.html', context)
