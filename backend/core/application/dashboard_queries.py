from __future__ import annotations

from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from compliance.models import AuditFinding, VATReconciliation, ZATCAInvoice, ZakatCalculation
from documents.models import Account, Document, Transaction


class DashboardSnapshotService:
    """Build the dashboard context in one place to keep the view thin."""

    def build(self, organization):
        findings = AuditFinding.objects.filter(organization=organization)

        stats = {
            'total_documents': Document.objects.filter(organization=organization).count(),
            'pending_documents': Document.objects.filter(organization=organization, status='pending').count(),
            'total_transactions': Transaction.objects.filter(organization=organization).count(),
            'total_accounts': Account.objects.filter(organization=organization).count(),
            'total_findings': findings.count(),
            'anomaly_count': Transaction.objects.filter(organization=organization, is_anomaly=True).count(),
        }

        total_findings = findings.count()
        resolved_findings = findings.filter(is_resolved=True).count()
        stats['compliance_score'] = (
            int((1 - (total_findings - resolved_findings) / max(total_findings, 1)) * 100)
            if total_findings > 0
            else 100
        )

        zatca_invoices = ZATCAInvoice.objects.filter(organization=organization)
        vat_reconciliations = VATReconciliation.objects.filter(organization=organization)
        zakat_calcs = ZakatCalculation.objects.filter(organization=organization)

        compliance_summary = {
            'zatca_checks': zatca_invoices.count(),
            'zatca_passed': zatca_invoices.filter(status='cleared').count() > 0 or zatca_invoices.count() == 0,
            'vat_reconciliations': vat_reconciliations.count(),
            'vat_variance': vat_reconciliations.aggregate(total=Sum('total_variance'))['total'] or Decimal('0'),
            'zakat_calculations': zakat_calcs.count(),
            'zakat_due': zakat_calcs.order_by('-fiscal_year_end').first().zakat_due if zakat_calcs.exists() else Decimal('0'),
        }

        recent_findings = findings.order_by('-created_at')[:5]
        anomalous_transactions = Transaction.objects.filter(
            organization=organization,
            is_anomaly=True,
        ).order_by('-transaction_date')[:5]
        recent_transactions = Transaction.objects.filter(organization=organization).order_by('-transaction_date')[:10]

        zatca_valid = zatca_invoices.filter(status__in=['validated', 'cleared']).count()
        zatca_score = int((zatca_valid / max(zatca_invoices.count(), 1)) * 100) if zatca_invoices.exists() else 100

        vat_score = vat_reconciliations.aggregate(avg=Sum('compliance_score'))['avg']
        vat_score = int(vat_score / max(vat_reconciliations.count(), 1)) if vat_score else 85

        zakat_score = zakat_calcs.aggregate(avg=Sum('compliance_score'))['avg']
        zakat_score = int(zakat_score / max(zakat_calcs.count(), 1)) if zakat_score else 90

        chart_data = {
            'compliance_scores': {
                'labels': ['ZATCA', 'ض.ق.م', 'الزكاة'],
                'values': [zatca_score, vat_score, zakat_score],
            },
            'findings_by_risk': {
                'labels': ['حرج', 'مرتفع', 'متوسط', 'منخفض'],
                'values': [
                    findings.filter(risk_level='critical').count(),
                    findings.filter(risk_level='high').count(),
                    findings.filter(risk_level='medium').count(),
                    findings.filter(risk_level='low').count(),
                ],
            },
        }

        return {
            'stats': stats,
            'compliance_summary': compliance_summary,
            'recent_findings': recent_findings,
            'anomalous_transactions': anomalous_transactions,
            'recent_transactions': recent_transactions,
            'chart_data': chart_data,
            'now': timezone.now(),
        }


dashboard_snapshot_service = DashboardSnapshotService()
