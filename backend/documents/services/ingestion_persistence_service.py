from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from documents.domain_signals import invoice_persisted
from documents.models import (
    Account,
    AuditTrail,
    Document,
    ExtractedData,
    FinancialBudget,
    InvoiceLineItem,
    InvoiceRecord,
    Vendor,
)

logger = logging.getLogger(__name__)

MONEY_PRECISION = Decimal('0.0001')
EXTRACTED_PRECISION = Decimal('0.01')
PRICE_PRECISION = Decimal('0.000001')
ZERO = Decimal('0')


@dataclass
class InvoicePersistenceResult:
    vendor: Vendor
    invoice: InvoiceRecord
    extracted_data: ExtractedData
    created_vendor: bool
    created_invoice: bool
    created_extracted_data: bool
    line_items_count: int
    audit_result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'status': 'saved',
            'vendor_id': str(self.vendor.id),
            'invoice_id': str(self.invoice.id),
            'extracted_data_id': str(self.extracted_data.id),
            'line_items_count': self.line_items_count,
            'created_vendor': self.created_vendor,
            'created_invoice': self.created_invoice,
            'created_extracted_data': self.created_extracted_data,
        }
        if self.audit_result:
            payload['audit'] = self.audit_result
        return payload


class InvoiceIngestionPersistenceService:
    """Persists extracted invoice JSON into relational models."""

    def normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Expose normalization so the workflow can track it as its own stage."""
        return self._normalize_payload(raw_payload)

    def persist(
        self,
        *,
        document: Document,
        raw_payload: Dict[str, Any],
        actor=None,
        extraction_provider: str = 'openai_vision',
        confidence: int = 0,
        extracted_data: Optional[ExtractedData] = None,
        normalized_payload: Optional[Dict[str, Any]] = None,
    ) -> InvoicePersistenceResult:
        organization = document.organization
        actor = actor or document.uploaded_by
        normalized = normalized_payload or self._normalize_payload(raw_payload)
        safe_raw_payload = self._make_json_safe(raw_payload)

        with transaction.atomic():
            vendor, created_vendor = self._resolve_vendor(
                organization=organization,
                actor=actor,
                normalized=normalized,
            )
            extracted_data_obj, created_extracted_data = self._upsert_extracted_data(
                document=document,
                extracted_data=extracted_data,
                vendor=vendor,
                normalized=normalized,
                raw_payload=safe_raw_payload,
                extraction_provider=extraction_provider,
                confidence=confidence,
            )
            invoice_record, created_invoice = self._upsert_invoice_record(
                document=document,
                extracted_data=extracted_data_obj,
                vendor=vendor,
                normalized=normalized,
                raw_payload=safe_raw_payload,
                actor=actor,
            )
            line_items_count = self._replace_line_items(invoice_record, normalized['items'])
            self._create_audit_trail(
                extracted_data=extracted_data_obj,
                actor=actor,
                vendor=vendor,
                invoice=invoice_record,
                line_items_count=line_items_count,
            )

            responses = invoice_persisted.send(
                sender=InvoiceRecord,
                invoice=invoice_record,
                extracted_data=extracted_data_obj,
                actor=actor,
            )
            audit_result = None
            for _, response in responses:
                if isinstance(response, dict):
                    audit_result = response
                    break

        return InvoicePersistenceResult(
            vendor=vendor,
            invoice=invoice_record,
            extracted_data=extracted_data_obj,
            created_vendor=created_vendor,
            created_invoice=created_invoice,
            created_extracted_data=created_extracted_data,
            line_items_count=line_items_count,
            audit_result=audit_result,
        )

    def _normalize_payload(self, raw_payload: Dict[str, Any]) -> Dict[str, Any]:
        vendor_data = raw_payload.get('vendor') if isinstance(raw_payload.get('vendor'), dict) else {}
        customer_data = raw_payload.get('customer') if isinstance(raw_payload.get('customer'), dict) else {}

        items = []
        raw_items = raw_payload.get('items') or raw_payload.get('line_items') or []
        for index, raw_item in enumerate(raw_items, start=1):
            if not isinstance(raw_item, dict):
                continue
            quantity = self._to_decimal(raw_item.get('quantity') or raw_item.get('qty') or 0, PRICE_PRECISION)
            unit_price = self._to_decimal(raw_item.get('unit_price') or raw_item.get('price') or 0, PRICE_PRECISION)
            line_total = self._to_decimal(
                raw_item.get('line_total') or raw_item.get('total') or raw_item.get('amount'),
                MONEY_PRECISION,
            )
            if line_total is None and quantity is not None and unit_price is not None:
                line_total = (quantity * unit_price).quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)
            items.append({
                'line_number': index,
                'description': self._clean_string(raw_item.get('description') or raw_item.get('product')),
                'quantity': quantity or ZERO,
                'unit_price': unit_price or ZERO,
                'line_total': line_total or ZERO,
                'raw_json': raw_item,
            })

        return {
            'invoice_number': self._clean_string(raw_payload.get('invoice_number')),
            'issue_date': self._parse_date(raw_payload.get('issue_date') or raw_payload.get('invoice_date')),
            'due_date': self._parse_date(raw_payload.get('due_date')),
            'vendor_name': self._clean_string(vendor_data.get('name') or raw_payload.get('vendor_name')),
            'vendor_tax_id': self._clean_string(
                vendor_data.get('tax_id')
                or vendor_data.get('vat_number')
                or raw_payload.get('vendor_tax_id')
                or raw_payload.get('vendor_vat_number')
            ),
            'vendor_commercial_registration': self._clean_string(
                vendor_data.get('commercial_registration')
                or vendor_data.get('registration_number')
                or raw_payload.get('vendor_commercial_registration')
                or raw_payload.get('vendor_cr')
            ),
            'vendor_address': self._clean_string(vendor_data.get('address') or raw_payload.get('vendor_address')),
            'customer_name': self._clean_string(customer_data.get('name') or raw_payload.get('customer_name')),
            'customer_tax_id': self._clean_string(
                customer_data.get('tax_id')
                or customer_data.get('vat_number')
                or raw_payload.get('customer_tax_id')
                or raw_payload.get('customer_vat_number')
            ),
            'currency': (self._clean_string(raw_payload.get('currency')) or 'SAR').upper(),
            'subtotal_amount': self._to_decimal(raw_payload.get('subtotal'), MONEY_PRECISION),
            'vat_amount': self._to_decimal(raw_payload.get('tax_amount') or raw_payload.get('vat_amount'), MONEY_PRECISION),
            'total_amount': self._to_decimal(raw_payload.get('total_amount'), MONEY_PRECISION),
            'cost_center': self._clean_string(raw_payload.get('cost_center') or raw_payload.get('cost_centre')),
            'budget_category': self._clean_string(raw_payload.get('budget_category')),
            'account_code': self._clean_string(raw_payload.get('account_code') or raw_payload.get('gl_account')),
            'items': items,
        }

    def _resolve_vendor(self, *, organization, actor, normalized):
        vendor_name = normalized['vendor_name'] or 'Unknown Vendor'
        vendor_tax_id = normalized['vendor_tax_id'] or None

        vendor = None
        created = False
        if vendor_tax_id:
            vendor, created = Vendor.objects.get_or_create(
                organization=organization,
                vat_number=vendor_tax_id,
                defaults={
                    'name': vendor_name,
                    'commercial_registration': normalized['vendor_commercial_registration'],
                    'address': normalized['vendor_address'],
                    'created_by': actor,
                },
            )
        else:
            vendor = Vendor.objects.filter(
                organization=organization,
                name__iexact=vendor_name,
            ).order_by('created_at').first()
            if vendor is None:
                vendor = Vendor.objects.create(
                    organization=organization,
                    name=vendor_name,
                    commercial_registration=normalized['vendor_commercial_registration'],
                    vat_number=None,
                    address=normalized['vendor_address'],
                    created_by=actor,
                )
                created = True

        update_fields = []
        if normalized['vendor_commercial_registration'] and not vendor.commercial_registration:
            vendor.commercial_registration = normalized['vendor_commercial_registration']
            update_fields.append('commercial_registration')
        if normalized['vendor_address'] and not vendor.address:
            vendor.address = normalized['vendor_address']
            update_fields.append('address')
        if normalized['vendor_tax_id'] and not vendor.vat_number:
            vendor.vat_number = normalized['vendor_tax_id']
            update_fields.append('vat_number')
        if update_fields:
            vendor.save(update_fields=update_fields)

        return vendor, created

    def _upsert_extracted_data(
        self,
        *,
        document,
        extracted_data,
        vendor,
        normalized,
        raw_payload,
        extraction_provider,
        confidence,
    ):
        payload = self._build_json_payload(normalized)
        defaults = {
            'organization': document.organization,
            'vendor_name': normalized['vendor_name'],
            'vendor_tax_id': normalized['vendor_tax_id'],
            'customer_name': normalized['customer_name'],
            'customer_tax_id': normalized['customer_tax_id'],
            'invoice_number': normalized['invoice_number'],
            'invoice_date': self._as_datetime(normalized['issue_date']),
            'due_date': self._as_datetime(normalized['due_date']),
            'subtotal_amount': normalized['subtotal_amount'],
            'total_amount': self._to_decimal(normalized['total_amount'], EXTRACTED_PRECISION),
            'tax_amount': self._to_decimal(normalized['vat_amount'], EXTRACTED_PRECISION),
            'currency': normalized['currency'],
            'raw_json': raw_payload,
            'items_json': payload['items'],
            'confidence': confidence,
            'validation_status': 'pending',
            'normalized_json': payload,
            'is_valid': False,
            'extraction_status': 'extracted',
            'extraction_provider': extraction_provider,
            'extraction_completed_at': timezone.now(),
        }

        if extracted_data is not None:
            created = False
            for field_name, value in defaults.items():
                setattr(extracted_data, field_name, value)
            extracted_data.save()
            return extracted_data, created

        extracted_data_obj, created = ExtractedData.objects.update_or_create(
            document=document,
            defaults=defaults,
        )
        return extracted_data_obj, created

    def _upsert_invoice_record(
        self,
        *,
        document,
        extracted_data,
        vendor,
        normalized,
        raw_payload,
        actor,
    ):
        organization = document.organization
        accounting_account = self._resolve_account(organization, normalized.get('account_code'))
        budget = self._resolve_budget(
            organization=organization,
            budget_category=normalized.get('budget_category') or normalized.get('cost_center'),
            issue_date=normalized.get('issue_date'),
        )
        defaults = {
            'organization': organization,
            'extracted_data': extracted_data,
            'vendor': vendor,
            'customer_organization': organization,
            'customer_name': normalized['customer_name'] or organization.name,
            'customer_vat_number': normalized['customer_tax_id'] or organization.vat_number,
            'invoice_number': normalized['invoice_number'],
            'issue_date': normalized['issue_date'],
            'due_date': normalized['due_date'],
            'currency': normalized['currency'],
            'subtotal_amount': normalized['subtotal_amount'],
            'vat_amount': normalized['vat_amount'],
            'total_amount': normalized['total_amount'],
            'cost_center': normalized['cost_center'],
            'accounting_account': accounting_account,
            'budget': budget,
            'raw_json': raw_payload,
            'created_by': actor,
        }

        existing = InvoiceRecord.objects.filter(document=document).first()
        if existing and existing.approval_status == 'approved':
            raise ValidationError('Approved invoices cannot be modified.')

        invoice_record, created = InvoiceRecord.objects.update_or_create(
            document=document,
            defaults=defaults,
        )
        return invoice_record, created

    def _replace_line_items(self, invoice_record, items):
        if invoice_record.approval_status == 'approved' and invoice_record.line_items.exists():
            raise ValidationError('Approved invoices cannot be modified.')

        invoice_record.line_items.all().delete()
        line_items = [
            InvoiceLineItem(
                invoice=invoice_record,
                line_number=item['line_number'],
                description=item['description'] or f"Line {item['line_number']}",
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                line_total=item['line_total'],
                raw_json=item['raw_json'],
            )
            for item in items
        ]
        if line_items:
            InvoiceLineItem.objects.bulk_create(line_items)
        return len(line_items)

    def _resolve_account(self, organization, account_code):
        if not account_code:
            return None
        return Account.objects.filter(
            organization=organization,
            account_code__iexact=account_code,
            is_active=True,
        ).first()

    def _resolve_budget(self, *, organization, budget_category, issue_date):
        if not budget_category or not issue_date:
            return None
        return FinancialBudget.objects.filter(
            organization=organization,
            category__iexact=budget_category,
            period_start__lte=issue_date,
            period_end__gte=issue_date,
        ).order_by('-period_start').first()

    def _create_audit_trail(self, *, extracted_data, actor, vendor, invoice, line_items_count):
        AuditTrail.objects.create(
            extracted_data=extracted_data,
            organization=extracted_data.organization,
            event_type='normalization',
            severity='info',
            title='Invoice persisted to ingestion layer',
            description='Vendor, invoice header, and line items were saved for audit readiness.',
            performed_by=actor,
            details={
                'vendor_id': str(vendor.id),
                'invoice_id': str(invoice.id),
                'line_items_count': line_items_count,
            },
            success=True,
            result_summary='Persistence completed successfully',
            phase='phase2',
        )

    def _build_json_payload(self, normalized):
        return {
            'invoice_number': normalized['invoice_number'],
            'issue_date': normalized['issue_date'].isoformat() if normalized['issue_date'] else None,
            'due_date': normalized['due_date'].isoformat() if normalized['due_date'] else None,
            'vendor_name': normalized['vendor_name'],
            'vendor_tax_id': normalized['vendor_tax_id'],
            'customer_name': normalized['customer_name'],
            'customer_tax_id': normalized['customer_tax_id'],
            'currency': normalized['currency'],
            'subtotal': self._decimal_to_json(normalized['subtotal_amount']),
            'tax_amount': self._decimal_to_json(normalized['vat_amount']),
            'total_amount': self._decimal_to_json(normalized['total_amount']),
            'items': [
                {
                    'line_number': item['line_number'],
                    'description': item['description'],
                    'quantity': self._decimal_to_json(item['quantity']),
                    'unit_price': self._decimal_to_json(item['unit_price']),
                    'line_total': self._decimal_to_json(item['line_total']),
                }
                for item in normalized['items']
            ],
        }

    @staticmethod
    def _clean_string(value: Any) -> Optional[str]:
        if value is None:
            return None
        cleaned = re.sub(r'\s+', ' ', str(value)).strip()
        return cleaned or None

    @staticmethod
    def _decimal_to_json(value: Optional[Decimal]) -> Optional[str]:
        return str(value) if value is not None else None

    @classmethod
    def _make_json_safe(cls, value: Any):
        if isinstance(value, dict):
            return {key: cls._make_json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._make_json_safe(item) for item in value]
        if isinstance(value, tuple):
            return [cls._make_json_safe(item) for item in value]
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def _parse_date(value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                return datetime.strptime(str(value).strip(), fmt).date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _as_datetime(value: Optional[date]) -> Optional[datetime]:
        if value is None:
            return None
        dt = datetime.combine(value, time.min)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt

    @staticmethod
    def _to_decimal(value: Any, precision: Decimal) -> Optional[Decimal]:
        if value in (None, ''):
            return None
        try:
            if isinstance(value, str):
                cleaned = re.sub(r'[^0-9,\.-]', '', value)
                if cleaned.count(',') == 1 and cleaned.count('.') == 0:
                    cleaned = cleaned.replace(',', '.')
                cleaned = cleaned.replace(',', '')
                value = cleaned
            decimal_value = Decimal(str(value))
            return decimal_value.quantize(precision, rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError):
            return None


invoice_ingestion_persistence_service = InvoiceIngestionPersistenceService()
