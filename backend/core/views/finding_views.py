"""
Finding Views - وجهات نتائج التدقيق
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST
import logging

from compliance.models import AuditFinding, AIExplanationLog

logger = logging.getLogger(__name__)


@login_required
def audit_findings_list_view(request):
    """قائمة نتائج التدقيق"""
    user = request.user
    organization = user.organization
    
    findings = AuditFinding.objects.filter(organization=organization)
    
    # Filters
    risk_level = request.GET.get('risk_level')
    finding_type = request.GET.get('finding_type')
    is_resolved = request.GET.get('is_resolved')
    
    if risk_level:
        findings = findings.filter(risk_level=risk_level)
    if finding_type:
        findings = findings.filter(finding_type=finding_type)
    if is_resolved is not None and is_resolved != '':
        findings = findings.filter(is_resolved=is_resolved == 'true')
    
    findings = findings.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(findings, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Stats for filters
    stats = {
        'total': AuditFinding.objects.filter(organization=organization).count(),
        'critical': AuditFinding.objects.filter(organization=organization, risk_level='critical').count(),
        'high': AuditFinding.objects.filter(organization=organization, risk_level='high').count(),
        'medium': AuditFinding.objects.filter(organization=organization, risk_level='medium').count(),
        'low': AuditFinding.objects.filter(organization=organization, risk_level='low').count(),
        'resolved': AuditFinding.objects.filter(organization=organization, is_resolved=True).count(),
        'unresolved': AuditFinding.objects.filter(organization=organization, is_resolved=False).count(),
    }
    
    context = {
        'findings': page_obj,
        'stats': stats,
        'current_risk_level': risk_level,
        'current_finding_type': finding_type,
        'current_is_resolved': is_resolved,
    }
    
    return render(request, 'findings/list.html', context)


@login_required
def audit_finding_detail_view(request, finding_id):
    """تفاصيل نتيجة التدقيق"""
    user = request.user
    organization = user.organization
    
    finding = get_object_or_404(AuditFinding, id=finding_id, organization=organization)
    
    # Get AI explanation logs for this finding
    ai_logs = finding.ai_explanation_logs.all().order_by('-generated_at')[:5]
    
    context = {
        'finding': finding,
        'ai_explanation_logs': ai_logs,
    }
    
    return render(request, 'findings/detail.html', context)


@login_required
def generate_ai_explanation_view(request, finding_id):
    """
    توليد شرح ذكي لنتيجة التدقيق
    Generate AI Explanation for Audit Finding
    
    COMPLIANCE:
    - Output is ADVISORY ONLY
    - Human review is REQUIRED
    - Full audit trail maintained
    """
    from compliance.ai_explanation_service import ai_explanation_service
    
    user = request.user
    organization = user.organization
    
    finding = get_object_or_404(AuditFinding, id=finding_id, organization=organization)
    
    if request.method == 'POST':
        try:
            # Get regulatory reference if available
            reg_ref = None
            if finding.regulatory_reference:
                reg_ref = f"{finding.regulatory_reference.article_number}: {finding.regulatory_reference.title_ar}"
            
            # Generate explanation asynchronously
            result = ai_explanation_service.generate_explanation_sync(
                finding_id=str(finding.id),
                title_ar=finding.title_ar,
                description_ar=finding.description_ar,
                risk_level=finding.risk_level,
                finding_type=finding.finding_type,
                financial_impact=finding.financial_impact,
                regulatory_reference=reg_ref,
            )
            
            if result.get('success'):
                # Store in audit log
                ai_log = AIExplanationLog.objects.create(
                    finding=finding,
                    organization=organization,
                    explanation_ar=result['explanation_ar'],
                    confidence_score=result['confidence_score'],
                    confidence_level=result['confidence_level'],
                    model_used=result['model_used'],
                    provider=result['provider'],
                    session_id=result['session_id'],
                    processing_time_ms=result['processing_time_ms'],
                    audit_hash=result['audit_hash'],
                    is_advisory=True,
                    requires_human_review=True,
                    generated_by=user,
                )
                
                # Update finding with new explanation (but keep human review required)
                finding.ai_explanation_ar = result['explanation_ar']
                finding.ai_confidence = result['confidence_score']
                finding.save()
                
                messages.success(
                    request, 
                    f'تم توليد الشرح الذكي بنجاح (درجة الثقة: {result["confidence_score"]}%). يرجى مراجعة الشرح قبل الاعتماد.'
                )
                
                logger.info(
                    f"AI explanation generated for finding {finding.finding_number} by {user.email}"
                )
            else:
                messages.error(
                    request, 
                    f'فشل في توليد الشرح الذكي: {result.get("error", "خطأ غير معروف")}'
                )
                
        except Exception as e:
            logger.error(f"AI explanation generation error: {e}")
            messages.error(request, f'خطأ في توليد الشرح الذكي: {str(e)}')
    
    return redirect('audit_finding_detail', finding_id=finding_id)


@login_required
@require_POST
def review_ai_explanation_view(request, log_id):
    """
    مراجعة واعتماد/رفض/تعديل الشرح الذكي
    Review and Approve/Reject/Modify AI Explanation
    
    COMPLIANCE:
    - All actions are logged
    - No automatic approval
    - No auto-override of audit findings
    - Preserves AIExplanationLog integrity
    """
    user = request.user
    organization = user.organization
    
    # Get the AI explanation log
    ai_log = get_object_or_404(AIExplanationLog, id=log_id, organization=organization)
    
    # Only pending logs can be reviewed
    if ai_log.approval_status != 'pending':
        messages.error(request, 'هذا الشرح تمت مراجعته مسبقاً')
        return redirect('audit_finding_detail', finding_id=ai_log.finding.id)
    
    action = request.POST.get('action', '')
    
    if action == 'approve':
        ai_log.approval_status = 'approved'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.save()
        
        messages.success(request, 'تم اعتماد الشرح الذكي بنجاح')
        logger.info(f"AI explanation approved: {ai_log.id} by {user.email}")
        
    elif action == 'reject':
        ai_log.approval_status = 'rejected'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.review_notes = request.POST.get('review_notes', 'رفض بدون ملاحظات')
        ai_log.save()
        
        messages.warning(request, 'تم رفض الشرح الذكي')
        logger.info(f"AI explanation rejected: {ai_log.id} by {user.email}")
        
    elif action == 'modify':
        modified_text = request.POST.get('modified_text', '').strip()
        review_notes = request.POST.get('review_notes', '').strip()
        
        if not modified_text:
            messages.error(request, 'يرجى إدخال النص المعدّل')
            return redirect('audit_finding_detail', finding_id=ai_log.finding.id)
        
        ai_log.approval_status = 'modified'
        ai_log.human_reviewed = True
        ai_log.reviewed_by = user
        ai_log.reviewed_at = timezone.now()
        ai_log.review_notes = review_notes or 'تم التعديل بواسطة المدقق'
        ai_log.explanation_ar = modified_text
        ai_log.save()
        
        # Update the finding with modified explanation
        ai_log.finding.ai_explanation_ar = modified_text
        ai_log.finding.save()
        
        messages.success(request, 'تم تعديل واعتماد الشرح الذكي')
        logger.info(f"AI explanation modified: {ai_log.id} by {user.email}")
    
    else:
        messages.error(request, 'إجراء غير صالح')
    
    return redirect('audit_finding_detail', finding_id=ai_log.finding.id)
