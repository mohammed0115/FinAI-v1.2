from __future__ import annotations

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from django.db.models import Avg, Count, Sum
from django.utils import timezone

from documents.models import AuditTrail, InvoiceAuditFinding, InvoiceLineItem, InvoiceRecord

logger = logging.getLogger(__name__)

TOLERANCE = Decimal('0.01')
PERCENT = Decimal('100')


class InvoiceIngestionAuditService:
    """Runs deterministic post-save audit procedures for ingested invoices."""

    def run_initial_checks(self, *, invoice: InvoiceRecord, extracted_data, actor=None) -> Dict[str, Any]:
        actor = actor or invoice.created_by or invoice.document.uploaded_by
        line_items = list(invoice.line_items.all().order_by('line_number'))
        same_vendor_invoices = InvoiceRecord.objects.filter(
            organization=invoice.organization,
            vendor=invoice.vendor,
        ).exclude(pk=invoice.pk)

        InvoiceAuditFinding.objects.filter(
            extracted_data=extracted_data,
            field__startswith='rule:',
        ).delete()

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        warnings: List[str] = []
        anomaly_flags: List[str] = []
        duplicate_score = 0
        duplicate_match = None

        def record(
            *,
            procedure: str,
            rule_key: str,
            status: str,
            severity: str,
            message: str,
            finding_type: str = 'other',
            field: Optional[str] = None,
            expected: Optional[Any] = None,
            actual: Optional[Any] = None,
            difference: Optional[Decimal] = None,
        ):
            result = {
                'procedure': procedure,
                'rule_key': rule_key,
                'status': status,
                'severity': severity,
                'message': message,
            }
            if expected is not None:
                result['expected'] = str(expected)
            if actual is not None:
                result['actual'] = str(actual)
            if difference is not None:
                result['difference'] = str(difference.quantize(TOLERANCE, rounding=ROUND_HALF_UP))
            results.append(result)

            if status == 'fail':
                errors.append(message)
            elif status == 'warning':
                warnings.append(message)

            if status in {'fail', 'warning'}:
                finding_field = f'rule:{rule_key}' if field is None else f'rule:{rule_key}:{field}'
                InvoiceAuditFinding.objects.create(
                    extracted_data=extracted_data,
                    organization=invoice.organization,
                    finding_type=finding_type,
                    severity=severity,
                    description=message,
                    field=finding_field,
                    expected_value=str(expected) if expected is not None else None,
                    actual_value=str(actual) if actual is not None else None,
                    difference=(difference.quantize(TOLERANCE, rounding=ROUND_HALF_UP) if difference is not None else None),
                )

        subtotal = invoice.subtotal_amount
        vat_amount = invoice.vat_amount or Decimal('0.0000')
        total_amount = invoice.total_amount
        line_sum = sum((line.line_total for line in line_items), Decimal('0.0000'))
        raw_json = invoice.raw_json or {}

        # Procedure 1: Header completeness
        record(
            procedure='header_completeness',
            rule_key='invoice_number_required',
            status='pass' if invoice.invoice_number else 'fail',
            severity='critical' if not invoice.invoice_number else 'info',
            message='Invoice number is present.' if invoice.invoice_number else 'Invoice must contain an invoice number.',
            finding_type='missing_field',
            field='invoice_number',
        )
        record(
            procedure='header_completeness',
            rule_key='invoice_date_required',
            status='pass' if invoice.issue_date else 'fail',
            severity='critical' if not invoice.issue_date else 'info',
            message='Invoice date is present.' if invoice.issue_date else 'Invoice must contain an issue date.',
            finding_type='missing_field',
            field='invoice_date',
        )
        record(
            procedure='header_completeness',
            rule_key='currency_required',
            status='pass' if invoice.currency else 'fail',
            severity='high' if not invoice.currency else 'info',
            message='Currency is present.' if invoice.currency else 'Currency must be specified on the invoice.',
            finding_type='missing_field',
            field='currency',
        )
        record(
            procedure='header_completeness',
            rule_key='total_amount_required',
            status='pass' if total_amount is not None else 'fail',
            severity='critical' if total_amount is None else 'info',
            message='Total amount is present.' if total_amount is not None else 'Invoice must contain a final total amount.',
            finding_type='missing_field',
            field='total_amount',
        )

        # Procedure 2: Party identity
        source_vendor_name = extracted_data.vendor_name
        source_vendor_vat = extracted_data.vendor_tax_id
        record(
            procedure='party_identity',
            rule_key='vendor_name_required',
            status='pass' if source_vendor_name else 'fail',
            severity='critical' if not source_vendor_name else 'info',
            message='Vendor name is present.' if source_vendor_name else 'Invoice must contain a vendor name.',
            finding_type='missing_field',
            field='vendor_name',
        )
        record(
            procedure='party_identity',
            rule_key='vendor_vat_required',
            status='pass' if source_vendor_vat else 'fail',
            severity='critical' if not source_vendor_vat else 'info',
            message='Vendor VAT number is present.' if source_vendor_vat else 'Invoice must contain a vendor VAT number.',
            finding_type='missing_field',
            field='vendor_tax_id',
        )
        customer_linked = bool(invoice.customer_organization_id)
        record(
            procedure='party_identity',
            rule_key='customer_linked_to_organization',
            status='pass' if customer_linked else 'fail',
            severity='high' if not customer_linked else 'info',
            message='Customer is linked to the tenant organization.' if customer_linked else 'Customer must be linked to the tenant organization.',
            finding_type='missing_field',
            field='customer_organization',
        )

        # Procedure 3: Line-item integrity
        if line_items:
            record(
                procedure='line_item_integrity',
                rule_key='line_items_present',
                status='pass',
                severity='info',
                message=f'{len(line_items)} line items were stored for this invoice.',
            )
        else:
            record(
                procedure='line_item_integrity',
                rule_key='line_items_present',
                status='warning',
                severity='medium',
                message='No line items were stored for this invoice.',
                finding_type='missing_field',
                field='items_json',
            )

        for line in line_items:
            expected_total = (line.quantity * line.unit_price).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            diff = abs(expected_total - line.line_total)
            record(
                procedure='line_item_integrity',
                rule_key=f'line_total_match_{line.line_number}',
                status='pass' if diff <= TOLERANCE else 'fail',
                severity='critical' if diff > TOLERANCE else 'info',
                message=(
                    f'Line {line.line_number} total matches quantity x unit price.'
                    if diff <= TOLERANCE
                    else f'Line {line.line_number} total mismatch: quantity x unit price = {expected_total}, line total = {line.line_total}.'
                ),
                finding_type='line_total_mismatch',
                field=f'line:{line.line_number}',
                expected=expected_total,
                actual=line.line_total,
                difference=diff,
            )

        # Procedure 4: Totals integrity
        if total_amount is not None and total_amount > 0:
            record(
                procedure='totals_integrity',
                rule_key='total_greater_than_zero',
                status='pass',
                severity='info',
                message='Final total is greater than zero.',
            )
        else:
            record(
                procedure='totals_integrity',
                rule_key='total_greater_than_zero',
                status='fail',
                severity='critical',
                message='Final total must be greater than zero.',
                finding_type='invalid_value',
                field='total_amount',
                actual=total_amount,
            )

        if vat_amount > 0 and not subtotal:
            record(
                procedure='totals_integrity',
                rule_key='vat_requires_subtotal',
                status='fail',
                severity='high',
                message='VAT cannot exist without a subtotal/base amount.',
                finding_type='vat_flag',
                field='subtotal_amount',
                actual=subtotal,
            )
        else:
            record(
                procedure='totals_integrity',
                rule_key='vat_requires_subtotal',
                status='pass',
                severity='info',
                message='VAT/base amount relationship is valid.',
            )

        derived_subtotal = subtotal if subtotal is not None else (line_sum if line_items else None)
        if derived_subtotal is not None and total_amount is not None:
            expected_total = (derived_subtotal + vat_amount).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            diff = abs(expected_total - total_amount)
            record(
                procedure='totals_integrity',
                rule_key='subtotal_plus_vat_equals_total',
                status='pass' if diff <= TOLERANCE else 'fail',
                severity='critical' if diff > TOLERANCE else 'info',
                message=(
                    'Subtotal plus VAT matches the final total.'
                    if diff <= TOLERANCE
                    else f'Subtotal plus VAT does not equal total. Expected {expected_total}, found {total_amount}.'
                ),
                finding_type='total_mismatch',
                field='total_amount',
                expected=expected_total,
                actual=total_amount,
                difference=diff,
            )
        else:
            record(
                procedure='totals_integrity',
                rule_key='subtotal_plus_vat_equals_total',
                status='warning',
                severity='medium',
                message='Could not fully verify subtotal plus VAT equals total because one of the values is missing.',
                finding_type='other',
                field='total_amount',
            )

        # Procedure 5: Duplicate logic
        same_number_qs = same_vendor_invoices.filter(invoice_number=invoice.invoice_number) if invoice.invoice_number else same_vendor_invoices.none()
        same_amount_date_qs = same_vendor_invoices.filter(total_amount=invoice.total_amount, issue_date=invoice.issue_date)
        same_hash_qs = InvoiceRecord.objects.filter(
            organization=invoice.organization,
            document__content_hash=invoice.document.content_hash,
        ).exclude(pk=invoice.pk) if invoice.document.content_hash else InvoiceRecord.objects.none()
        different_month_qs = same_number_qs.exclude(issue_date__month=invoice.issue_date.month, issue_date__year=invoice.issue_date.year) if invoice.issue_date and invoice.invoice_number else same_vendor_invoices.none()

        if same_number_qs.exists():
            duplicate_score = max(duplicate_score, 95)
            duplicate_match = duplicate_match or same_number_qs.first()
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_vendor_invoice_number',
                status='fail',
                severity='critical',
                message='Duplicate detected: same vendor and same invoice number already exist.',
                finding_type='other',
                field='invoice_number',
                actual=invoice.invoice_number,
            )
        else:
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_vendor_invoice_number',
                status='pass',
                severity='info',
                message='No duplicate found for vendor + invoice number.',
            )

        if same_amount_date_qs.exists():
            duplicate_score = max(duplicate_score, 85)
            duplicate_match = duplicate_match or same_amount_date_qs.first()
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_vendor_amount_date',
                status='warning',
                severity='high',
                message='Potential duplicate detected: same vendor, same amount, and same date exist.',
                finding_type='other',
                field='total_amount',
                actual=invoice.total_amount,
            )
        else:
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_vendor_amount_date',
                status='pass',
                severity='info',
                message='No duplicate found for vendor + amount + date.',
            )

        if same_hash_qs.exists():
            duplicate_score = max(duplicate_score, 100)
            duplicate_match = duplicate_match or same_hash_qs.first()
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_document_hash',
                status='fail',
                severity='critical',
                message='The same document content hash was uploaded more than once.',
                finding_type='other',
                field='document_hash',
                actual=invoice.document.content_hash,
            )
        else:
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_document_hash',
                status='pass',
                severity='info',
                message='No duplicate upload detected from document hash.',
            )

        if different_month_qs.exists():
            duplicate_score = max(duplicate_score, 75)
            duplicate_match = duplicate_match or different_month_qs.first()
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_different_month',
                status='warning',
                severity='high',
                message='Invoice number for this vendor appears again in a different accounting month.',
                finding_type='other',
                field='invoice_number',
                actual=invoice.invoice_number,
            )
        else:
            record(
                procedure='duplicate_logic',
                rule_key='duplicate_different_month',
                status='pass',
                severity='info',
                message='No duplicate found across different months for this vendor/invoice number.',
            )

        # Procedure 6: VAT rules
        is_saudi_context = invoice.organization.country == 'SA' or invoice.currency == 'SAR'
        if subtotal and subtotal > 0 and vat_amount is not None:
            vat_rate = ((vat_amount / subtotal) * PERCENT).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if is_saudi_context:
                rate_diff = abs(vat_rate - Decimal('15.00'))
                record(
                    procedure='vat_rules',
                    rule_key='saudi_vat_rate_15',
                    status='pass' if rate_diff <= Decimal('0.50') else 'fail',
                    severity='high' if rate_diff > Decimal('0.50') else 'info',
                    message=(
                        'Saudi VAT rate is consistent with 15%.'
                        if rate_diff <= Decimal('0.50')
                        else f'Saudi VAT rate should be 15%, but calculated rate is {vat_rate}%.'
                    ),
                    finding_type='vat_flag',
                    field='vat_amount',
                    expected='15.00',
                    actual=vat_rate,
                    difference=rate_diff,
                )
                expected_vat = (subtotal * Decimal('0.15')).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                vat_diff = abs(expected_vat - vat_amount)
                record(
                    procedure='vat_rules',
                    rule_key='vat_calculation_correct',
                    status='pass' if vat_diff <= TOLERANCE else 'fail',
                    severity='high' if vat_diff > TOLERANCE else 'info',
                    message=(
                        'VAT calculation is correct.'
                        if vat_diff <= TOLERANCE
                        else f'VAT calculation is incorrect. Expected {expected_vat}, found {vat_amount}.'
                    ),
                    finding_type='vat_flag',
                    field='vat_amount',
                    expected=expected_vat,
                    actual=vat_amount,
                    difference=vat_diff,
                )
            else:
                record(
                    procedure='vat_rules',
                    rule_key='vat_calculation_correct',
                    status='pass',
                    severity='info',
                    message='VAT percentage is computable for this invoice.',
                )
        else:
            record(
                procedure='vat_rules',
                rule_key='vat_calculation_correct',
                status='warning',
                severity='medium',
                message='VAT calculation could not be fully verified because subtotal or VAT amount is missing.',
                finding_type='vat_flag',
                field='vat_amount',
            )

        qr_present = any(raw_json.get(key) for key in ('qr_code', 'qr_data', 'zatca_qr', 'has_qr_code'))
        if is_saudi_context:
            record(
                procedure='vat_rules',
                rule_key='qr_code_present',
                status='pass' if qr_present else 'warning',
                severity='medium' if not qr_present else 'info',
                message='QR code evidence is present for the invoice.' if qr_present else 'Saudi invoice QR code was not extracted for verification.',
                finding_type='other',
                field='qr_code',
            )
        else:
            record(
                procedure='vat_rules',
                rule_key='qr_code_present',
                status='pass',
                severity='info',
                message='QR code validation is not required for this invoice context.',
            )

        # Procedure 7: Vendor behaviour
        historical_vendor_count = same_vendor_invoices.count()
        if historical_vendor_count == 0:
            anomaly_flags.append('new_vendor')
            record(
                procedure='vendor_behavior',
                rule_key='vendor_first_seen',
                status='warning',
                severity='medium',
                message='Vendor is appearing for the first time in this organization.',
                finding_type='other',
                field='vendor',
            )
        else:
            record(
                procedure='vendor_behavior',
                rule_key='vendor_first_seen',
                status='pass',
                severity='info',
                message='Vendor has prior history in this organization.',
            )

        historical_average = same_vendor_invoices.aggregate(avg_total=Avg('total_amount'))['avg_total']
        if historical_average and invoice.total_amount and invoice.total_amount > historical_average * Decimal('3'):
            anomaly_flags.append('amount_outlier')
            record(
                procedure='vendor_behavior',
                rule_key='amount_higher_than_usual',
                status='warning',
                severity='high',
                message=f'Invoice total {invoice.total_amount} is much higher than vendor average {historical_average}.',
                finding_type='other',
                field='total_amount',
                expected=historical_average,
                actual=invoice.total_amount,
                difference=invoice.total_amount - historical_average,
            )
        else:
            record(
                procedure='vendor_behavior',
                rule_key='amount_higher_than_usual',
                status='pass',
                severity='info',
                message='Invoice amount is within normal vendor range or no baseline exists yet.',
            )

        current_month = invoice.issue_date.replace(day=1) if invoice.issue_date else timezone.now().date().replace(day=1)
        vendor_spend = InvoiceRecord.objects.filter(
            organization=invoice.organization,
            vendor=invoice.vendor,
            issue_date__gte=current_month,
        ).exclude(pk=invoice.pk).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        org_spend = InvoiceRecord.objects.filter(
            organization=invoice.organization,
            issue_date__gte=current_month,
        ).exclude(pk=invoice.pk).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        if org_spend > 0 and vendor_spend / org_spend >= Decimal('0.60'):
            anomaly_flags.append('vendor_concentration')
            record(
                procedure='vendor_behavior',
                rule_key='vendor_concentration',
                status='warning',
                severity='high',
                message='One vendor represents most invoice spend this month.',
                finding_type='other',
                field='vendor',
                actual=(vendor_spend / org_spend * PERCENT).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            )
        else:
            record(
                procedure='vendor_behavior',
                rule_key='vendor_concentration',
                status='pass',
                severity='info',
                message='Vendor concentration is within acceptable range.',
            )

        # Procedure 8: Volume and timing
        if invoice.issue_date:
            same_day_count = InvoiceRecord.objects.filter(
                organization=invoice.organization,
                issue_date=invoice.issue_date,
            ).exclude(pk=invoice.pk).count()
            if same_day_count >= 10:
                anomaly_flags.append('high_same_day_volume')
                record(
                    procedure='volume_and_timing',
                    rule_key='many_invoices_same_day',
                    status='warning',
                    severity='medium',
                    message=f'{same_day_count + 1} invoices exist for the same day.',
                    finding_type='other',
                    field='invoice_date',
                    actual=same_day_count + 1,
                )
            else:
                record(
                    procedure='volume_and_timing',
                    rule_key='many_invoices_same_day',
                    status='pass',
                    severity='info',
                    message='Same-day invoice volume is normal.',
                )

            if invoice.issue_date.month in {12} or (invoice.issue_date.month in {3, 6, 9} and invoice.issue_date.day >= 25):
                recent_count = InvoiceRecord.objects.filter(
                    organization=invoice.organization,
                    issue_date__year=invoice.issue_date.year,
                    issue_date__month=invoice.issue_date.month,
                ).count()
                if recent_count >= 10:
                    anomaly_flags.append('year_end_cluster')
                    record(
                        procedure='volume_and_timing',
                        rule_key='year_end_invoice_cluster',
                        status='warning',
                        severity='medium',
                        message='High invoice volume detected near fiscal period end.',
                        finding_type='other',
                        field='invoice_date',
                    )
                else:
                    record(
                        procedure='volume_and_timing',
                        rule_key='year_end_invoice_cluster',
                        status='pass',
                        severity='info',
                        message='No unusual year-end invoice cluster detected.',
                    )
            else:
                record(
                    procedure='volume_and_timing',
                    rule_key='year_end_invoice_cluster',
                    status='pass',
                    severity='info',
                    message='Invoice is outside fiscal year-end cluster window.',
                )
        else:
            record(
                procedure='volume_and_timing',
                rule_key='many_invoices_same_day',
                status='warning',
                severity='medium',
                message='Could not evaluate same-day volume because invoice date is missing.',
                finding_type='other',
                field='invoice_date',
            )
            record(
                procedure='volume_and_timing',
                rule_key='year_end_invoice_cluster',
                status='warning',
                severity='low',
                message='Could not evaluate year-end clustering because invoice date is missing.',
                finding_type='other',
                field='invoice_date',
            )

        # Procedure 9: Price patterns
        price_change_detected = False
        for line in line_items:
            historical_stats = InvoiceLineItem.objects.filter(
                invoice__organization=invoice.organization,
                invoice__vendor=invoice.vendor,
                description__iexact=line.description,
            ).exclude(invoice=invoice).aggregate(avg_price=Avg('unit_price'), samples=Count('id'))
            avg_price = historical_stats['avg_price']
            samples = historical_stats['samples'] or 0
            if avg_price and samples >= 2:
                upper = avg_price * Decimal('1.50')
                lower = avg_price * Decimal('0.50')
                if line.unit_price > upper or line.unit_price < lower:
                    price_change_detected = True
                    anomaly_flags.append(f'price_change_line_{line.line_number}')
                    record(
                        procedure='price_patterns',
                        rule_key=f'price_change_{line.line_number}',
                        status='warning',
                        severity='high',
                        message=f'Line {line.line_number} unit price {line.unit_price} changed sharply from historical average {avg_price}.',
                        finding_type='other',
                        field=f'line:{line.line_number}:unit_price',
                        expected=avg_price,
                        actual=line.unit_price,
                        difference=abs(line.unit_price - avg_price),
                    )
        if not price_change_detected:
            record(
                procedure='price_patterns',
                rule_key='price_change_detected',
                status='pass',
                severity='info',
                message='No sudden price changes detected against historical line-item prices.',
            )

        # Procedure 10: Financial controls and governance
        record(
            procedure='financial_controls',
            rule_key='cost_center_linked',
            status='pass' if invoice.cost_center else 'warning',
            severity='medium' if not invoice.cost_center else 'info',
            message='Invoice is linked to a cost center.' if invoice.cost_center else 'Invoice should be linked to a cost center.',
            finding_type='missing_field',
            field='cost_center',
        )
        record(
            procedure='financial_controls',
            rule_key='accounting_account_linked',
            status='pass' if invoice.accounting_account_id else 'warning',
            severity='medium' if not invoice.accounting_account_id else 'info',
            message='Invoice is linked to an accounting account.' if invoice.accounting_account_id else 'Invoice should be linked to an accounting account.',
            finding_type='missing_field',
            field='accounting_account',
        )

        if invoice.budget_id and invoice.total_amount is not None:
            budget_limit = invoice.budget.revised_budget or invoice.budget.budget_amount
            projected_spend = (invoice.budget.actual_spend or Decimal('0')) + invoice.total_amount
            budget_diff = projected_spend - budget_limit
            record(
                procedure='financial_controls',
                rule_key='within_budget',
                status='pass' if budget_diff <= TOLERANCE else 'fail',
                severity='high' if budget_diff > TOLERANCE else 'info',
                message='Invoice is within the linked budget.' if budget_diff <= TOLERANCE else 'Invoice exceeds the linked budget.',
                finding_type='other',
                field='budget',
                expected=budget_limit,
                actual=projected_spend,
                difference=budget_diff if budget_diff > 0 else Decimal('0'),
            )
        else:
            record(
                procedure='financial_controls',
                rule_key='within_budget',
                status='warning',
                severity='medium',
                message='Invoice is not linked to an active budget for validation.',
                finding_type='missing_field',
                field='budget',
            )

        if invoice.approval_status == 'approved' and not invoice.approved_by_id:
            record(
                procedure='governance',
                rule_key='approved_by_recorded',
                status='fail',
                severity='high',
                message='Approved invoice must record who approved it.',
                finding_type='missing_field',
                field='approved_by',
            )
        else:
            record(
                procedure='governance',
                rule_key='approved_by_recorded',
                status='pass',
                severity='info',
                message='Approval metadata is consistent with invoice state.',
            )

        has_audit_trail = extracted_data.audit_trails.exists()
        record(
            procedure='governance',
            rule_key='audit_trail_exists',
            status='pass' if has_audit_trail else 'fail',
            severity='high' if not has_audit_trail else 'info',
            message='Audit trail exists for the invoice.' if has_audit_trail else 'Every invoice edit must be captured in the audit trail.',
            finding_type='other',
            field='audit_trail',
        )

        anomaly_score = min(100, len(anomaly_flags) * 15 + (duplicate_score // 2))
        extracted_data.validation_errors = errors
        extracted_data.validation_warnings = warnings
        extracted_data.compliance_checks = results
        extracted_data.is_valid = len(errors) == 0
        extracted_data.validation_status = 'validated' if len(errors) == 0 else 'rejected'
        extracted_data.validation_completed_at = timezone.now()
        extracted_data.duplicate_score = duplicate_score
        extracted_data.duplicate_matched_document = (
            duplicate_match.extracted_data if duplicate_match and duplicate_match.extracted_data_id else None
        )
        extracted_data.anomaly_flags = anomaly_flags
        extracted_data.anomaly_score = anomaly_score
        extracted_data.cross_document_findings_count = len([r for r in results if r['procedure'] == 'duplicate_logic' and r['status'] != 'pass'])
        extracted_data.save(
            update_fields=[
                'validation_errors',
                'validation_warnings',
                'compliance_checks',
                'is_valid',
                'validation_status',
                'validation_completed_at',
                'duplicate_score',
                'duplicate_matched_document',
                'anomaly_flags',
                'anomaly_score',
                'cross_document_findings_count',
            ]
        )

        AuditTrail.objects.create(
            extracted_data=extracted_data,
            organization=invoice.organization,
            event_type='validation',
            severity='error' if errors else ('warning' if warnings else 'info'),
            title='Initial audit procedures completed',
            description='Deterministic invoice audit checks were executed after persistence.',
            performed_by=actor,
            details={
                'invoice_id': str(invoice.id),
                'procedures_run': 10,
                'checks_run': len(results),
                'error_count': len(errors),
                'warning_count': len(warnings),
            },
            success=len(errors) == 0,
            result_summary=f'Errors: {len(errors)} | Warnings: {len(warnings)}',
            phase='phase2',
        )

        logger.info(
            'Initial ingestion audit completed for invoice %s with %s errors and %s warnings',
            invoice.id,
            len(errors),
            len(warnings),
        )
        return {
            'procedures_run': 10,
            'checks_run': len(results),
            'errors_count': len(errors),
            'warnings_count': len(warnings),
            'finding_count': InvoiceAuditFinding.objects.filter(
                extracted_data=extracted_data,
                field__startswith='rule:',
            ).count(),
            'duplicate_score': duplicate_score,
            'anomaly_score': anomaly_score,
        }


invoice_ingestion_audit_service = InvoiceIngestionAuditService()
