"""
Compliance Views - وجهات الامتثال
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from decimal import Decimal
import logging

from core.models import Organization
from compliance.models import (
    AuditFinding, ZATCAInvoice, VATReconciliation, 
    ZakatCalculation, RegulatoryReference, ZATCAVerificationLog
)

logger = logging.getLogger(__name__)


@login_required
def compliance_overview_view(request):
    """صفحة نظرة عامة على الامتثال"""
    user = request.user
    organization = user.organization
    
    # ZATCA Summary
    zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
    zatca_summary = {
        'total': zatca_invoices.count(),
        'validated': zatca_invoices.filter(status='validated').count(),
        'cleared': zatca_invoices.filter(status='cleared').count(),
        'rejected': zatca_invoices.filter(status='rejected').count(),
        'pending': zatca_invoices.filter(status='pending').count(),
    }
    
    # Calculate ZATCA score
    zatca_valid = zatca_summary['validated'] + zatca_summary['cleared']
    zatca_score = int((zatca_valid / max(zatca_summary['total'], 1)) * 100) if zatca_summary['total'] > 0 else 100
    
    # VAT Summary
    vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
    vat_summary = {
        'total': vat_reconciliations.count(),
        'total_variance': vat_reconciliations.aggregate(total=Sum('total_variance'))['total'] or Decimal('0'),
        'total_collected': vat_reconciliations.aggregate(total=Sum('total_output_vat'))['total'] or Decimal('0'),
        'total_reported': vat_reconciliations.aggregate(total=Sum('total_reported'))['total'] or Decimal('0'),
    }
    vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
    vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 100
    
    # Zakat Summary
    zakat_calcs = ZakatCalculation.objects.filter(organization=organization)
    latest_zakat = zakat_calcs.order_by('-fiscal_year_end').first()
    zakat_summary = {
        'total': zakat_calcs.count(),
        'latest': latest_zakat,
        'zakat_due': latest_zakat.zakat_due if latest_zakat else Decimal('0'),
        'zakat_base': latest_zakat.zakat_base if latest_zakat else Decimal('0'),
    }
    zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
    zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 100
    
    # Overall score
    overall_score = int((zatca_score + vat_score + zakat_score) / 3)
    
    # Recent regulatory references
    regulatory_refs = RegulatoryReference.objects.all()[:10]
    
    context = {
        'zatca_summary': zatca_summary,
        'zatca_score': zatca_score,
        'vat_summary': vat_summary,
        'vat_score': vat_score,
        'zakat_summary': zakat_summary,
        'zakat_score': zakat_score,
        'overall_score': overall_score,
        'regulatory_refs': regulatory_refs,
    }
    
    return render(request, 'compliance/overview.html', context)


@login_required
def zatca_verification_view(request):
    """
    صفحة التحقق من الفواتير عبر ZATCA API
    ZATCA Invoice Verification Page
    
    SCOPE: VERIFICATION ONLY - No submission, clearance, or signing
    """
    from compliance.zatca_api_service import zatca_api_service
    
    user = request.user
    organization = user.organization
    
    verification_result = None
    
    if request.method == 'POST':
        verification_type = request.POST.get('verification_type', 'vat')
        
        if verification_type == 'vat':
            vat_number = request.POST.get('vat_number', '').strip()
            if vat_number:
                verification_result = zatca_api_service.verify_vat_number(vat_number)
                
                # Store as audit evidence
                ZATCAVerificationLog.objects.create(
                    organization=organization,
                    verification_type='vat_number',
                    input_identifier=vat_number,
                    is_valid=verification_result.get('valid', False),
                    compliance_score=100 if verification_result.get('valid') else 0,
                    passed_checks=1 if verification_result.get('valid') else 0,
                    failed_checks=0 if verification_result.get('valid') else 1,
                    message_ar=verification_result.get('message_ar') or verification_result.get('error_message_ar'),
                    message_en=verification_result.get('message_en'),
                    error_code=verification_result.get('error_code'),
                    response_json=verification_result,
                    processing_time_ms=verification_result.get('processing_time_ms', 0),
                    audit_hash=verification_result.get('audit_hash', ''),
                    verified_by=user,
                )
                
                if verification_result.get('valid'):
                    messages.success(request, verification_result.get('message_ar', 'تم التحقق بنجاح'))
                else:
                    messages.error(request, verification_result.get('error_message_ar', 'فشل التحقق'))
        
        elif verification_type == 'invoice':
            invoice_xml = request.POST.get('invoice_xml', '')
            invoice_hash = request.POST.get('invoice_hash', '')
            invoice_uuid = request.POST.get('invoice_uuid', '')
            
            if invoice_xml and invoice_uuid:
                verification_result = zatca_api_service.verify_invoice_structure(
                    invoice_xml, invoice_hash, invoice_uuid
                )
                
                # Store as audit evidence
                ZATCAVerificationLog.objects.create(
                    organization=organization,
                    verification_type='invoice_structure',
                    input_identifier=invoice_uuid,
                    is_valid=verification_result.get('valid', False),
                    compliance_score=verification_result.get('compliance_score', 0),
                    passed_checks=verification_result.get('passed_count', 0),
                    failed_checks=verification_result.get('failed_count', 0),
                    message_ar=verification_result.get('message_ar'),
                    message_en=verification_result.get('message_en'),
                    response_json=verification_result,
                    processing_time_ms=verification_result.get('processing_time_ms', 0),
                    audit_hash=verification_result.get('audit_hash', ''),
                    verified_by=user,
                )
                
                if verification_result.get('valid'):
                    messages.success(request, verification_result.get('message_ar', 'تم التحقق بنجاح'))
                else:
                    messages.error(request, verification_result.get('message_ar', 'فشل التحقق'))
    
    # Get recent verifications
    recent_verifications = ZATCAVerificationLog.objects.filter(
        organization=organization
    ).order_by('-created_at')[:10]
    
    context = {
        'verification_result': verification_result,
        'recent_verifications': recent_verifications,
        'scope_docs': zatca_api_service.get_scope_documentation(),
    }
    
    return render(request, 'compliance/zatca_verification.html', context)
