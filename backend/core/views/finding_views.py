import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone

from compliance.models import AIExplanationLog, AuditFinding
from core.views.base import OrganizationActionView, OrganizationTemplateView

logger = logging.getLogger(__name__)


class AuditFindingsListPageView(OrganizationTemplateView):
    template_name = 'findings/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = self.get_organization()
        findings = AuditFinding.objects.filter(organization=organization)

        risk_level = self.request.GET.get('risk_level')
        finding_type = self.request.GET.get('finding_type')
        is_resolved = self.request.GET.get('is_resolved')

        if risk_level:
            findings = findings.filter(risk_level=risk_level)
        if finding_type:
            findings = findings.filter(finding_type=finding_type)
        if is_resolved not in (None, ''):
            findings = findings.filter(is_resolved=is_resolved == 'true')

        findings = findings.order_by('-created_at')
        page_obj = Paginator(findings, 20).get_page(self.request.GET.get('page'))

        context.update(
            {
                'findings': page_obj,
                'stats': {
                    'total': AuditFinding.objects.filter(organization=organization).count(),
                    'critical': AuditFinding.objects.filter(organization=organization, risk_level='critical').count(),
                    'high': AuditFinding.objects.filter(organization=organization, risk_level='high').count(),
                    'medium': AuditFinding.objects.filter(organization=organization, risk_level='medium').count(),
                    'low': AuditFinding.objects.filter(organization=organization, risk_level='low').count(),
                    'resolved': AuditFinding.objects.filter(organization=organization, is_resolved=True).count(),
                    'unresolved': AuditFinding.objects.filter(organization=organization, is_resolved=False).count(),
                },
                'current_risk_level': risk_level,
                'current_finding_type': finding_type,
                'current_is_resolved': is_resolved,
            }
        )
        return context


class AuditFindingDetailPageView(OrganizationTemplateView):
    template_name = 'findings/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        finding = get_object_or_404(
            AuditFinding,
            id=self.kwargs['finding_id'],
            organization=self.get_organization(),
        )
        context.update(
            {
                'finding': finding,
                'ai_explanation_logs': finding.ai_explanation_logs.all().order_by('-generated_at')[:5],
            }
        )
        return context


class GenerateAIExplanationView(OrganizationActionView):
    def post(self, request, *args, **kwargs):
        from compliance.ai_explanation_service import ai_explanation_service

        finding = get_object_or_404(
            AuditFinding,
            id=kwargs['finding_id'],
            organization=self.get_organization(),
        )

        try:
            regulatory_reference = None
            if finding.regulatory_reference:
                regulatory_reference = f'{finding.regulatory_reference.article_number}: {finding.regulatory_reference.title_ar}'

            result = ai_explanation_service.generate_explanation_sync(
                finding_id=str(finding.id),
                title_ar=finding.title_ar,
                description_ar=finding.description_ar,
                risk_level=finding.risk_level,
                finding_type=finding.finding_type,
                financial_impact=finding.financial_impact,
                regulatory_reference=regulatory_reference,
            )

            if result.get('success'):
                AIExplanationLog.objects.create(
                    finding=finding,
                    organization=self.get_organization(),
                    explanation_ar=result['explanation_ar'],
                    confidence_score=result['confidence_score'],
                    confidence_level=result['confidence_level'],
                    regulatory_context=regulatory_reference,
                    ai_model=result['model_used'],
                    prompt_version=result['prompt_version'],
                    processing_time_ms=result['processing_time_ms'],
                    requires_human_review=True,
                    generated_by=request.user,
                )

                finding.ai_explanation_ar = result['explanation_ar']
                finding.ai_confidence = result['confidence_score']
                finding.save()
                messages.success(request, f'تم توليد الشرح الذكي بنجاح (درجة الثقة: {result["confidence_score"]}%). يرجى مراجعة الشرح قبل الاعتماد.')
                logger.info('AI explanation generated for finding %s by %s', finding.finding_number, request.user.email)
            else:
                messages.error(request, f'فشل في توليد الشرح الذكي: {result.get("error", "خطأ غير معروف")}')
        except Exception as exc:
            logger.error('AI explanation generation error: %s', exc)
            messages.error(request, f'خطأ في توليد الشرح الذكي: {exc}')

        return redirect('audit_finding_detail', finding_id=finding.id)


class ReviewAIExplanationView(OrganizationActionView):
    def post(self, request, *args, **kwargs):
        ai_log = get_object_or_404(AIExplanationLog, id=kwargs['log_id'], organization=self.get_organization())

        if ai_log.approval_status != 'pending':
            messages.error(request, 'هذا الشرح تمت مراجعته مسبقاً')
            return redirect('audit_finding_detail', finding_id=ai_log.finding.id)

        action_name = request.POST.get('action', '')
        if action_name == 'approve':
            ai_log.approval_status = 'approved'
            ai_log.human_reviewed = True
            ai_log.reviewed_by = request.user
            ai_log.reviewed_at = timezone.now()
            ai_log.save()
            messages.success(request, 'تم اعتماد الشرح الذكي بنجاح')
        elif action_name == 'reject':
            ai_log.approval_status = 'rejected'
            ai_log.human_reviewed = True
            ai_log.reviewed_by = request.user
            ai_log.reviewed_at = timezone.now()
            ai_log.review_notes = request.POST.get('review_notes', 'رفض بدون ملاحظات')
            ai_log.save()
            messages.warning(request, 'تم رفض الشرح الذكي')
        elif action_name == 'modify':
            modified_text = request.POST.get('modified_text', '').strip()
            review_notes = request.POST.get('review_notes', '').strip()
            if not modified_text:
                messages.error(request, 'يرجى إدخال النص المعدل')
                return redirect('audit_finding_detail', finding_id=ai_log.finding.id)

            ai_log.approval_status = 'modified'
            ai_log.human_reviewed = True
            ai_log.reviewed_by = request.user
            ai_log.reviewed_at = timezone.now()
            ai_log.review_notes = review_notes or 'تم التعديل بواسطة المدقق'
            ai_log.explanation_ar = modified_text
            ai_log.save()

            ai_log.finding.ai_explanation_ar = modified_text
            ai_log.finding.save()
            messages.success(request, 'تم تعديل واعتماد الشرح الذكي')
        else:
            messages.error(request, 'إجراء غير صالح')

        return redirect('audit_finding_detail', finding_id=ai_log.finding.id)


audit_findings_list_view = AuditFindingsListPageView.as_view()
audit_finding_detail_view = AuditFindingDetailPageView.as_view()
generate_ai_explanation_view = GenerateAIExplanationView.as_view()
review_ai_explanation_view = ReviewAIExplanationView.as_view()


__all__ = [
    'AuditFindingsListPageView',
    'AuditFindingDetailPageView',
    'GenerateAIExplanationView',
    'ReviewAIExplanationView',
    'audit_findings_list_view',
    'audit_finding_detail_view',
    'generate_ai_explanation_view',
    'review_ai_explanation_view',
]
