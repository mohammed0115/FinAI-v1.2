import logging

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

from core.models import Organization
from core.vat_validation_service import vat_validation_service
from core.views.base import OrganizationActionView, OrganizationTemplateView

logger = logging.getLogger(__name__)


class ToggleLanguageView(OrganizationActionView):
    require_organization = False

    def post(self, request, *args, **kwargs):
        current_lang = request.session.get('language', 'ar')
        request.session['language'] = 'en' if current_lang == 'ar' else 'ar'
        return redirect(request.META.get('HTTP_REFERER', '/'))


class OrganizationSettingsPageView(OrganizationTemplateView):
    template_name = 'settings/organization.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        context.update(
            {
                'vat_requirements': vat_validation_service.get_country_vat_requirements(organization.country),
                'all_country_requirements': {
                    code: vat_validation_service.get_country_vat_requirements(code)
                    for code, _ in Organization.COUNTRY_CHOICES
                },
                'validation_result': kwargs.get('validation_result'),
                'country_choices': Organization.COUNTRY_CHOICES,
                'company_type_choices': Organization.COMPANY_TYPE_CHOICES,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        organization = self.get_organization()

        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        country = request.POST.get('country', organization.country)
        vat_number = request.POST.get('vat_number', '').strip()
        company_type = request.POST.get('company_type', '')
        industry = request.POST.get('industry', '').strip()
        lang = request.session.get('language', 'ar')

        validation_result = vat_validation_service.validate_vat_number(
            vat_number=vat_number,
            country=country,
            lang=lang,
        )

        if validation_result['valid']:
            organization.name = name or organization.name
            organization.name_ar = name_ar
            organization.country = country
            organization.vat_number = vat_number if vat_number else None
            organization.vat_applicable = validation_result['vat_applicable']
            organization.zatca_enabled = validation_result['zatca_enabled']
            organization.company_type = company_type or None
            organization.industry = industry or None

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
            organization.zatca_verification_scope = 'verification_only' if organization.zatca_enabled else 'disabled'
            organization.save()

            messages.success(request, 'تم حفظ إعدادات الشركة بنجاح')
            logger.info('Organization settings updated: %s by %s', organization.name, request.user.email)
            return redirect('organization_settings')

        messages.error(request, validation_result['error_message'])
        return render(request, self.template_name, self.get_context_data(validation_result=validation_result))


toggle_language_view = ToggleLanguageView.as_view()
organization_settings_view = OrganizationSettingsPageView.as_view()


__all__ = [
    'ToggleLanguageView',
    'OrganizationSettingsPageView',
    'toggle_language_view',
    'organization_settings_view',
]
