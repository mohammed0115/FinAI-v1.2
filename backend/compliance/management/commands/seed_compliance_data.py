"""
Seed regulatory references and compliance test data
بذر البيانات التنظيمية وبيانات اختبار الامتثال
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random

from core.models import User, Organization
from compliance.models import (
    RegulatoryReference, ZATCAInvoice, ZATCAValidationResult,
    VATReconciliation, VATDiscrepancy, ZakatCalculation,
    ZakatDiscrepancy, AuditFinding
)


class Command(BaseCommand):
    help = 'Seed compliance test data - بذر بيانات اختبار الامتثال'

    def handle(self, *args, **options):
        self.stdout.write('Starting compliance data seeding...\n')
        
        try:
            with transaction.atomic():
                # Create regulatory references
                self.create_regulatory_references()
                
                # Get organizations
                orgs = Organization.objects.filter(country='SA')
                if not orgs.exists():
                    self.stdout.write(self.style.WARNING('No Saudi organizations found'))
                    return
                
                # Create compliance data for each org
                for org in orgs:
                    users = User.objects.filter(organization=org)
                    if users.exists():
                        user = users.first()
                        self.create_zatca_invoices(org, user)
                        self.create_vat_reconciliation(org, user)
                        self.create_zakat_calculation(org, user)
                        self.create_audit_findings(org, user)
                
                self.stdout.write(self.style.SUCCESS('\n=== Compliance data seeding complete ==='))
                self.print_summary()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise

    def create_regulatory_references(self):
        """Create ZATCA regulatory references"""
        self.stdout.write('Creating regulatory references...')
        
        references = [
            # VAT References
            {
                'regulator': 'zatca',
                'category': 'vat',
                'article_number': 'المادة 53',
                'title_ar': 'الفاتورة الضريبية',
                'title_en': 'Tax Invoice Requirements',
                'description_ar': 'يجب على الخاضع للضريبة إصدار فاتورة ضريبية أصلية تتضمن البيانات الإلزامية عند القيام بتوريد السلع أو الخدمات',
                'description_en': 'A taxable person must issue an original tax invoice containing mandatory data when supplying goods or services',
                'penalty_description_ar': 'غرامة مالية تتراوح بين 5,000 و 50,000 ريال سعودي',
                'penalty_amount_min': 5000,
                'penalty_amount_max': 50000,
            },
            {
                'regulator': 'zatca',
                'category': 'vat',
                'article_number': 'المادة 40',
                'title_ar': 'تقديم الإقرار الضريبي',
                'title_en': 'Tax Return Submission',
                'description_ar': 'يجب على كل شخص خاضع للضريبة تقديم إقرار ضريبي عن كل فترة ضريبية خلال الموعد المحدد',
                'description_en': 'Every taxable person must submit a tax return for each tax period within the specified deadline',
                'penalty_description_ar': 'غرامة تأخير 5-25% من الضريبة المستحقة',
                'penalty_amount_min': 0,
                'penalty_amount_max': 0,
            },
            # E-Invoicing References
            {
                'regulator': 'zatca',
                'category': 'einvoice',
                'article_number': 'قرار هيئة الزكاة والضريبة والجمارك',
                'title_ar': 'متطلبات الفوترة الإلكترونية',
                'title_en': 'E-Invoicing Requirements',
                'description_ar': 'إلزام جميع المكلفين بإصدار وحفظ الفواتير إلكترونياً وفقاً للائحة الفوترة الإلكترونية',
                'description_en': 'All taxpayers must issue and store invoices electronically according to the e-invoicing regulations',
                'penalty_description_ar': 'غرامة 10,000 - 50,000 ريال عن كل مخالفة',
                'penalty_amount_min': 10000,
                'penalty_amount_max': 50000,
            },
            # Zakat References
            {
                'regulator': 'zatca',
                'category': 'zakat',
                'article_number': 'المادة 2',
                'title_ar': 'وعاء الزكاة',
                'title_en': 'Zakat Base',
                'description_ar': 'يتكون وعاء الزكاة من رأس المال والأرباح المحتجزة والمخصصات والالتزامات طويلة الأجل',
                'description_en': 'The Zakat base consists of capital, retained earnings, provisions, and long-term liabilities',
                'penalty_description_ar': 'غرامة على التأخير في السداد',
                'penalty_amount_min': 0,
                'penalty_amount_max': 0,
            },
            {
                'regulator': 'zatca',
                'category': 'zakat',
                'article_number': 'المادة 8',
                'title_ar': 'معدل الزكاة',
                'title_en': 'Zakat Rate',
                'description_ar': 'نسبة الزكاة 2.5% من الوعاء الزكوي السنوي',
                'description_en': 'The Zakat rate is 2.5% of the annual Zakat base',
                'penalty_description_ar': 'لا توجد غرامة - الزكاة واجبة شرعاً',
                'penalty_amount_min': 0,
                'penalty_amount_max': 0,
            },
            # AML References
            {
                'regulator': 'zatca',
                'category': 'aml',
                'article_number': 'نظام مكافحة غسل الأموال',
                'title_ar': 'الإبلاغ عن العمليات المشبوهة',
                'title_en': 'Suspicious Transaction Reporting',
                'description_ar': 'يجب الإبلاغ عن أي عمليات مالية مشبوهة تتجاوز الحدود المقررة',
                'description_en': 'Any suspicious financial transactions exceeding the set limits must be reported',
                'penalty_description_ar': 'عقوبات جنائية ومالية',
                'penalty_amount_min': 100000,
                'penalty_amount_max': 5000000,
            },
        ]
        
        for ref_data in references:
            RegulatoryReference.objects.get_or_create(
                regulator=ref_data['regulator'],
                article_number=ref_data['article_number'],
                defaults=ref_data
            )
        
        self.stdout.write(f'  Created {len(references)} regulatory references')

    def create_zatca_invoices(self, org, user):
        """Create sample ZATCA invoices"""
        self.stdout.write(f'Creating ZATCA invoices for {org.name}...')
        
        customers = [
            ('شركة النور للتجارة', '310123456700003'),
            ('مؤسسة الخليج', '310987654300003'),
            ('شركة الرياض التقنية', '310111222300003'),
        ]
        
        for i in range(10):
            customer_name, customer_vat = random.choice(customers)
            total_ex_vat = Decimal(random.randint(5000, 50000))
            vat_amount = (total_ex_vat * Decimal('0.15')).quantize(Decimal('0.01'))
            total_inc_vat = total_ex_vat + vat_amount
            
            # Some invoices have issues for testing
            has_issue = random.random() < 0.2
            if has_issue:
                # Invalid VAT calculation
                vat_amount = Decimal(random.randint(100, 1000))
                total_inc_vat = total_ex_vat + vat_amount
            
            issue_date = timezone.now().date() - timedelta(days=random.randint(1, 90))
            
            ZATCAInvoice.objects.create(
                organization=org,
                invoice_number=f'INV-{org.country}-{timezone.now().strftime("%Y%m")}-{i+1:05d}',
                invoice_type_code='388',
                invoice_subtype='0100000',
                issue_date=issue_date,
                issue_time=timezone.now().time(),
                seller_name=org.name,
                seller_vat_number=org.tax_id or '310000000000003',
                seller_address='الرياض، المملكة العربية السعودية',
                seller_city='الرياض',
                seller_postal_code='12345',
                buyer_name=customer_name,
                buyer_vat_number=customer_vat,
                buyer_city='جدة',
                total_excluding_vat=total_ex_vat,
                total_vat=vat_amount,
                total_including_vat=total_inc_vat,
                line_items_json=[
                    {
                        'name': 'خدمات استشارية',
                        'quantity': 1,
                        'unit_price': float(total_ex_vat),
                        'vat_rate': 15,
                    }
                ],
                status='draft' if has_issue else 'validated',
                created_by=user,
            )
        
        self.stdout.write(f'  Created 10 ZATCA invoices')

    def create_vat_reconciliation(self, org, user):
        """Create VAT reconciliation records"""
        self.stdout.write(f'Creating VAT reconciliation for {org.name}...')
        
        # Last quarter
        period_end = timezone.now().date().replace(day=1) - timedelta(days=1)
        period_start = period_end.replace(day=1) - timedelta(days=60)
        period_start = period_start.replace(day=1)
        
        output_vat = Decimal(random.randint(50000, 200000))
        input_vat = Decimal(random.randint(20000, 80000))
        net_vat = output_vat - input_vat
        gl_vat = net_vat + Decimal(random.randint(-1000, 1000))  # Small variance
        variance = net_vat - gl_vat
        
        recon = VATReconciliation.objects.create(
            organization=org,
            period_type='quarterly',
            period_start=period_start,
            period_end=period_end,
            output_vat_sales=output_vat,
            total_output_vat=output_vat,
            input_vat_purchases=input_vat,
            total_input_vat=input_vat,
            net_vat_due=net_vat,
            gl_vat_payable_balance=gl_vat,
            total_variance=variance,
            variance_explanation_ar='فروقات توقيت في تسجيل بعض الفواتير',
            compliance_score=85 if abs(variance) < 5000 else 70,
            status='completed',
            prepared_by=user,
        )
        
        # Add discrepancies
        if abs(variance) > 100:
            VATDiscrepancy.objects.create(
                reconciliation=recon,
                discrepancy_type='timing',
                expected_vat=net_vat,
                actual_vat=gl_vat,
                variance=variance,
                description_ar='فرق توقيت في تسجيل الفواتير بين نظام المبيعات والنظام المحاسبي',
                description_en='Timing difference between sales system and accounting system',
            )
        
        self.stdout.write(f'  Created VAT reconciliation with variance {variance}')

    def create_zakat_calculation(self, org, user):
        """Create Zakat calculation"""
        self.stdout.write(f'Creating Zakat calculation for {org.name}...')
        
        fiscal_year_end = date(timezone.now().year - 1, 12, 31)
        fiscal_year_start = date(timezone.now().year - 1, 1, 1)
        
        equity = Decimal(random.randint(1000000, 5000000))
        liabilities = Decimal(random.randint(200000, 1000000))
        provisions = Decimal(random.randint(50000, 200000))
        profit = Decimal(random.randint(100000, 500000))
        
        positive_base = equity + liabilities + provisions + profit
        
        fixed_assets = Decimal(random.randint(300000, 800000))
        losses = Decimal(random.randint(0, 100000))
        deductions = fixed_assets + losses
        
        net_base = max(positive_base - deductions, Decimal('0'))
        zakat_due = net_base * Decimal('0.025')
        
        ZakatCalculation.objects.create(
            organization=org,
            fiscal_year_start=fiscal_year_start,
            fiscal_year_end=fiscal_year_end,
            total_equity=equity,
            long_term_liabilities=liabilities,
            provisions=provisions,
            adjusted_net_profit=profit,
            positive_zakat_base=positive_base,
            fixed_assets=fixed_assets,
            accumulated_losses=losses,
            total_deductions=deductions,
            net_zakat_base=net_base,
            zakat_due=zakat_due,
            compliance_score=90,
            status='calculated',
            prepared_by=user,
        )
        
        self.stdout.write(f'  Created Zakat calculation: {zakat_due:,.2f} SAR due')

    def create_audit_findings(self, org, user):
        """Create audit findings with Arabic content"""
        self.stdout.write(f'Creating audit findings for {org.name}...')
        
        findings_data = [
            {
                'finding_type': 'compliance',
                'risk_level': 'high',
                'title_ar': 'عدم تقديم إقرار ضريبة القيمة المضافة في الموعد المحدد',
                'title_en': 'Late VAT Return Submission',
                'description_ar': 'تم رصد تأخر في تقديم إقرار ضريبة القيمة المضافة للربع الثالث من عام 2024 بمدة 15 يوم عن الموعد النظامي',
                'description_en': 'VAT return for Q3 2024 was submitted 15 days late',
                'impact_ar': 'قد يؤدي التأخير إلى فرض غرامات مالية من هيئة الزكاة والضريبة والجمارك',
                'recommendation_ar': 'إنشاء نظام تذكير آلي للمواعيد الضريبية وتعيين مسؤول للمتابعة',
                'financial_impact': 25000,
            },
            {
                'finding_type': 'accuracy',
                'risk_level': 'medium',
                'title_ar': 'أخطاء في حساب ضريبة القيمة المضافة',
                'title_en': 'VAT Calculation Errors',
                'description_ar': 'تم رصد 5 فواتير تحتوي على أخطاء في حساب ضريبة القيمة المضافة بقيمة إجمالية 3,500 ريال',
                'description_en': '5 invoices with VAT calculation errors totaling SAR 3,500',
                'impact_ar': 'يؤثر على دقة الإقرار الضريبي وقد يتطلب تصحيح',
                'recommendation_ar': 'مراجعة إعدادات نظام الفوترة والتأكد من صحة نسب الضريبة المطبقة',
                'financial_impact': 3500,
            },
            {
                'finding_type': 'documentation',
                'risk_level': 'medium',
                'title_ar': 'نقص في المستندات الداعمة',
                'title_en': 'Missing Supporting Documents',
                'description_ar': 'لم يتم العثور على المستندات الداعمة لعدد 12 معاملة مالية',
                'description_en': 'Supporting documents missing for 12 financial transactions',
                'impact_ar': 'يؤثر على إمكانية التحقق من صحة المعاملات أثناء الفحص الضريبي',
                'recommendation_ar': 'تطبيق سياسة صارمة لحفظ المستندات وأرشفتها إلكترونياً',
                'financial_impact': 0,
            },
            {
                'finding_type': 'internal_control',
                'risk_level': 'critical',
                'title_ar': 'ضعف في الفصل بين الصلاحيات',
                'title_en': 'Segregation of Duties Weakness',
                'description_ar': 'تم رصد أن نفس الموظف يقوم بإدخال المعاملات والموافقة عليها دون مراجعة',
                'description_en': 'Same employee enters and approves transactions without review',
                'impact_ar': 'يزيد من مخاطر الاحتيال والأخطاء غير المكتشفة',
                'recommendation_ar': 'تطبيق مبدأ الفصل بين الصلاحيات وإنشاء سلسلة موافقات متعددة المستويات',
                'financial_impact': 0,
            },
        ]
        
        reg_ref = RegulatoryReference.objects.filter(category='vat').first()
        
        for i, data in enumerate(findings_data):
            AuditFinding.objects.create(
                organization=org,
                finding_number=f'FND-{org.country}-{timezone.now().strftime("%Y")}-{i+1:03d}',
                regulatory_reference=reg_ref,
                ai_explanation_ar='تم اكتشاف هذه الملاحظة من خلال تحليل الذكاء الاصطناعي للمعاملات المالية',
                ai_confidence=random.randint(75, 95),
                is_resolved=random.random() < 0.3,
                identified_by=user,
                **data
            )
        
        self.stdout.write(f'  Created {len(findings_data)} audit findings')

    def print_summary(self):
        """Print summary"""
        self.stdout.write('\n=== COMPLIANCE DATA SUMMARY ===')
        self.stdout.write(f'Regulatory References: {RegulatoryReference.objects.count()}')
        self.stdout.write(f'ZATCA Invoices: {ZATCAInvoice.objects.count()}')
        self.stdout.write(f'VAT Reconciliations: {VATReconciliation.objects.count()}')
        self.stdout.write(f'Zakat Calculations: {ZakatCalculation.objects.count()}')
        self.stdout.write(f'Audit Findings: {AuditFinding.objects.count()}')
