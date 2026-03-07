"""
Management command to generate audit reports for extracted data
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from documents.models import ExtractedData, InvoiceAuditReport
from documents.services import InvoiceAuditReportService
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class Command(BaseCommand):
    help = 'Generate comprehensive audit reports for invoice data'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate reports for ALL extracted data (even if report exists)',
        )
        parser.add_argument(
            '--org',
            type=str,
            help='Generate reports only for specific organization ID',
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of reports to generate',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting audit report generation...'))
        
        # Get extracted data that doesn't have reports yet
        query = ExtractedData.objects.all()
        
        if options['org']:
            query = query.filter(organization_id=options['org'])
        
        if not options['all']:
            # Only include records without reports
            query = query.exclude(audit_report__isnull=False)
        
        if options['limit']:
            query = query[:options['limit']]
        
        total = query.count()
        self.stdout.write(f'Found {total} records to process')
        
        if total == 0:
            self.stdout.write(self.style.WARNING('No records to process'))
            return
        
        # Get a default user (system user)
        try:
            system_user = User.objects.filter(role='admin').first()
            if not system_user:
                system_user = User.objects.first()
        except:
            system_user = None
        
        generated = 0
        failed = 0
        skipped = 0
        
        service = InvoiceAuditReportService(user=system_user)
        
        for idx, extracted_data in enumerate(query, 1):
            try:
                # Check if report already exists
                if not options['all'] and hasattr(extracted_data, 'audit_report') and extracted_data.audit_report:
                    self.stdout.write(f'[{idx}/{total}] Skipping (report exists): {extracted_data.invoice_number}')
                    skipped += 1
                    continue
                
                # Get OCR evidence
                ocr_evidence = extracted_data.document.ocr_evidence_records.first()
                
                # Generate report
                report = service.generate_comprehensive_report(
                    extracted_data=extracted_data,
                    document=extracted_data.document,
                    organization=extracted_data.organization,
                    ocr_evidence=ocr_evidence
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'[{idx}/{total}] Generated: {report.report_number} - '
                        f'{extracted_data.invoice_number} (Risk: {report.risk_level})'
                    )
                )
                generated += 1
            
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'[{idx}/{total}] Failed: {extracted_data.invoice_number} - {str(e)}'
                    )
                )
                failed += 1
                logger.error(f'Error generating report for {extracted_data.id}: {e}', exc_info=True)
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(self.style.SUCCESS(f'Generated: {generated}'))
        self.stdout.write(self.style.WARNING(f'Failed: {failed}'))
        self.stdout.write(self.style.WARNING(f'Skipped: {skipped}'))
        self.stdout.write(self.style.SUCCESS(f'Total: {total}'))
