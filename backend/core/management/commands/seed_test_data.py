"""
Management command to seed test data for FinAI platform.
Creates synthetic but realistic financial data for manual testing.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random
import uuid

from core.models import User, Organization, AuditLog
from documents.models import (
    Document, ExtractedData, Transaction, Account,
    JournalEntry, JournalEntryLine, ComplianceCheck, AuditFlag
)
from reports.models import Report, Insight


class Command(BaseCommand):
    help = 'Seed database with comprehensive test data for manual testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write('Starting test data seeding...\n')
        
        if options['clear']:
            self.clear_data()
        
        try:
            with transaction.atomic():
                # Create organizations
                orgs = self.create_organizations()
                
                # Create users for each org
                users = self.create_users(orgs)
                
                # Create chart of accounts for each org
                accounts = self.create_accounts(orgs)
                
                # Create transactions (normal and anomalous)
                transactions = self.create_transactions(orgs, users, accounts)
                
                # Create journal entries
                self.create_journal_entries(orgs, users, accounts)
                
                # Create compliance checks
                self.create_compliance_checks(orgs, users, transactions)
                
                # Create audit flags
                self.create_audit_flags(orgs, users, transactions)
                
                # Create insights
                self.create_insights(orgs)
                
                # Create reports
                self.create_reports(orgs, users)
                
                # Create audit logs
                self.create_audit_logs(orgs, users)
                
                self.stdout.write(self.style.SUCCESS('\n=== Test data seeding complete ==='))
                self.print_summary()
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during seeding: {str(e)}'))
            raise

    def clear_data(self):
        """Clear existing test data"""
        self.stdout.write('Clearing existing data...')
        AuditFlag.objects.all().delete()
        ComplianceCheck.objects.all().delete()
        JournalEntryLine.objects.all().delete()
        JournalEntry.objects.all().delete()
        Transaction.objects.all().delete()
        Account.objects.all().delete()
        ExtractedData.objects.all().delete()
        Document.objects.all().delete()
        Insight.objects.all().delete()
        Report.objects.all().delete()
        AuditLog.objects.all().delete()
        # Keep admin users, delete test users
        User.objects.filter(email__contains='test').delete()
        # Keep demo org, delete test orgs
        Organization.objects.exclude(name='FinAI Demo Company').delete()
        self.stdout.write(self.style.SUCCESS('✓ Existing data cleared'))

    def create_organizations(self):
        """Create test organizations across GCC"""
        self.stdout.write('Creating organizations...')
        
        org_data = [
            {
                'name': 'Al-Faisal Trading Company',
                'country': 'SA',
                'tax_id': '3100123456',
                'vat_rate': 15,
                'currency': 'SAR',
                'industry': 'Wholesale Trade',
                'company_type': 'private',
            },
            {
                'name': 'Emirates Tech Solutions',
                'country': 'AE',
                'tax_id': '100234567890123',
                'vat_rate': 5,
                'currency': 'AED',
                'industry': 'Information Technology',
                'company_type': 'sme',
            },
            {
                'name': 'Kuwait Industrial Group',
                'country': 'KW',
                'tax_id': 'KW123456789',
                'vat_rate': 0,  # Kuwait has no VAT yet
                'currency': 'KWD',
                'industry': 'Manufacturing',
                'company_type': 'private',
            },
        ]
        
        orgs = []
        for data in org_data:
            org, created = Organization.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            orgs.append(org)
            status = 'Created' if created else 'Exists'
            self.stdout.write(f'  {status}: {org.name} ({org.country})')
        
        return orgs

    def create_users(self, orgs):
        """Create test users for each organization"""
        self.stdout.write('Creating users...')
        
        users = {}
        roles = ['auditor', 'accountant', 'finance_manager']
        
        for org in orgs:
            org_users = []
            for role in roles:
                email = f'test.{role}@{org.name.lower().replace(" ", "")}.com'
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'name': f'Test {role.title()} - {org.name[:20]}',
                        'role': role,
                        'organization': org,
                    }
                )
                if created:
                    user.set_password(f'{role}123')
                    user.save()
                org_users.append(user)
            users[org.id] = org_users
            self.stdout.write(f'  Created {len(org_users)} users for {org.name}')
        
        return users

    def create_accounts(self, orgs):
        """Create chart of accounts for each organization"""
        self.stdout.write('Creating chart of accounts...')
        
        # Standard chart of accounts template
        account_template = [
            # Assets (1xxx)
            ('1000', 'Cash in Bank', 'النقدية في البنك', 'asset', 'cash'),
            ('1001', 'Petty Cash', 'الصندوق', 'asset', 'cash'),
            ('1100', 'Accounts Receivable', 'الذمم المدينة', 'asset', 'accounts_receivable'),
            ('1200', 'Inventory', 'المخزون', 'asset', 'inventory'),
            ('1300', 'Prepaid Expenses', 'المصروفات المدفوعة مقدماً', 'asset', 'prepaid'),
            ('1500', 'Equipment', 'المعدات', 'asset', 'fixed_assets'),
            ('1510', 'Vehicles', 'المركبات', 'asset', 'fixed_assets'),
            ('1600', 'Accumulated Depreciation', 'مجمع الإهلاك', 'asset', 'fixed_assets'),
            
            # Liabilities (2xxx)
            ('2000', 'Accounts Payable', 'الذمم الدائنة', 'liability', 'accounts_payable'),
            ('2100', 'VAT Payable', 'ضريبة القيمة المضافة المستحقة', 'liability', 'vat_payable'),
            ('2200', 'Salaries Payable', 'الرواتب المستحقة', 'liability', 'accrued'),
            ('2500', 'Short-term Loans', 'قروض قصيرة الأجل', 'liability', 'loans'),
            ('2600', 'Long-term Loans', 'قروض طويلة الأجل', 'liability', 'loans'),
            
            # Equity (3xxx)
            ('3000', 'Share Capital', 'رأس المال', 'equity', 'capital'),
            ('3100', 'Retained Earnings', 'الأرباح المحتجزة', 'equity', 'retained_earnings'),
            ('3200', 'Current Year Earnings', 'أرباح السنة الحالية', 'equity', 'retained_earnings'),
            
            # Revenue (4xxx)
            ('4000', 'Sales Revenue', 'إيرادات المبيعات', 'revenue', 'sales'),
            ('4100', 'Service Revenue', 'إيرادات الخدمات', 'revenue', 'service_income'),
            ('4200', 'Interest Income', 'إيرادات الفوائد', 'revenue', 'other_income'),
            ('4300', 'Other Income', 'إيرادات أخرى', 'revenue', 'other_income'),
            
            # Expenses (5xxx)
            ('5000', 'Cost of Goods Sold', 'تكلفة البضاعة المباعة', 'expense', 'cost_of_goods'),
            ('5100', 'Salaries & Wages', 'الرواتب والأجور', 'expense', 'salaries'),
            ('5200', 'Rent Expense', 'مصروف الإيجار', 'expense', 'rent'),
            ('5300', 'Utilities', 'المرافق', 'expense', 'utilities'),
            ('5400', 'Marketing & Advertising', 'التسويق والإعلان', 'expense', 'marketing'),
            ('5500', 'Professional Fees', 'أتعاب مهنية', 'expense', 'other_expense'),
            ('5600', 'Depreciation', 'الإهلاك', 'expense', 'other_expense'),
            ('5700', 'Bank Charges', 'مصاريف بنكية', 'expense', 'other_expense'),
            ('5800', 'Office Supplies', 'لوازم مكتبية', 'expense', 'other_expense'),
        ]
        
        accounts = {}
        for org in orgs:
            org_accounts = []
            for code, name, name_ar, acc_type, subtype in account_template:
                # Add random opening balance for balance sheet accounts
                opening_balance = Decimal('0')
                if acc_type in ['asset', 'liability', 'equity']:
                    if acc_type == 'asset':
                        opening_balance = Decimal(random.randint(10000, 500000))
                    elif acc_type == 'liability':
                        opening_balance = Decimal(random.randint(5000, 200000))
                    elif acc_type == 'equity':
                        opening_balance = Decimal(random.randint(100000, 1000000))
                
                account = Account.objects.create(
                    organization=org,
                    account_code=code,
                    account_name=name,
                    account_name_ar=name_ar,
                    account_type=acc_type,
                    account_subtype=subtype,
                    currency=org.currency,
                    opening_balance=opening_balance,
                    current_balance=opening_balance,
                )
                org_accounts.append(account)
            
            accounts[org.id] = {acc.account_code: acc for acc in org_accounts}
            self.stdout.write(f'  Created {len(org_accounts)} accounts for {org.name}')
        
        return accounts

    def create_transactions(self, orgs, users, accounts):
        """Create transactions - normal and anomalous"""
        self.stdout.write('Creating transactions...')
        
        # Vendors/Customers
        vendors = [
            'ABC Suppliers', 'XYZ Corporation', 'Global Parts Ltd',
            'Tech Solutions Inc', 'Office World', 'Building Materials Co',
            'Shipping Express', 'Al-Salam Enterprises', 'Gulf Trading LLC'
        ]
        
        customers = [
            'Acme Corp', 'Best Buy Co', 'City Motors', 'Delta Industries',
            'Eastern Traders', 'First Choice LLC', 'Golden Star', 'Horizon Group'
        ]
        
        all_transactions = {}
        
        for org in orgs:
            org_transactions = []
            org_users = users.get(org.id, [])
            org_accounts = accounts.get(org.id, {})
            
            if not org_users:
                continue
            
            # Generate 100 transactions per organization over last 6 months
            base_date = timezone.now() - timedelta(days=180)
            
            for i in range(100):
                # 80% normal, 15% anomalous, 5% compliance violations
                is_anomaly = random.random() < 0.15
                is_violation = random.random() < 0.05
                
                # Random date within last 6 months
                days_offset = random.randint(0, 180)
                txn_date = base_date + timedelta(days=days_offset)
                
                # Determine transaction type
                if random.random() < 0.6:  # 60% income
                    txn_type = 'income'
                    amount = Decimal(random.randint(5000, 100000))
                    account = org_accounts.get('4000')  # Sales Revenue
                    vendor_customer = random.choice(customers)
                    category = 'Sales'
                else:  # 40% expense
                    txn_type = 'expense'
                    amount = Decimal(random.randint(1000, 50000))
                    expense_accounts = ['5000', '5100', '5200', '5300', '5400']
                    account = org_accounts.get(random.choice(expense_accounts))
                    vendor_customer = random.choice(vendors)
                    category = account.account_name if account else 'General'
                
                # Make some transactions anomalous
                anomaly_type = None
                if is_anomaly:
                    anomaly_types = [
                        ('unusual_amount', lambda a: a * Decimal('5')),  # 5x normal
                        ('round_number', lambda a: Decimal(str(int(a/1000)*1000))),
                        ('duplicate', lambda a: a),
                    ]
                    anomaly_type, amount_fn = random.choice(anomaly_types)
                    amount = amount_fn(amount)
                
                # Calculate VAT
                vat_rate = Decimal(str(org.vat_rate))
                if vat_rate > 0:
                    vat_amount = (amount * vat_rate / Decimal('100')).quantize(Decimal('0.01'))
                else:
                    vat_amount = Decimal('0')
                
                # Create compliance violation
                if is_violation:
                    vat_amount = Decimal('0')  # Missing VAT
                
                txn = Transaction.objects.create(
                    organization=org,
                    account=account,
                    transaction_type=txn_type,
                    category=category,
                    amount=amount,
                    currency=org.currency,
                    description=f"{'Invoice' if txn_type == 'income' else 'Payment'} - {vendor_customer}",
                    transaction_date=txn_date,
                    account_code=account.account_code if account else None,
                    vendor_customer=vendor_customer,
                    vat_amount=vat_amount,
                    vat_rate=vat_rate,
                    is_reconciled=random.random() < 0.7,  # 70% reconciled
                    is_anomaly=is_anomaly,
                    anomaly_type=anomaly_type,
                    reference_number=f"TXN-{org.country}-{i+1:05d}",
                    created_by=random.choice(org_users),
                )
                org_transactions.append(txn)
            
            all_transactions[org.id] = org_transactions
            anomaly_count = sum(1 for t in org_transactions if t.is_anomaly)
            self.stdout.write(
                f'  Created {len(org_transactions)} transactions for {org.name} '
                f'({anomaly_count} anomalies)'
            )
        
        return all_transactions

    def create_journal_entries(self, orgs, users, accounts):
        """Create journal entries for double-entry bookkeeping"""
        self.stdout.write('Creating journal entries...')
        
        for org in orgs:
            org_users = users.get(org.id, [])
            org_accounts = accounts.get(org.id, {})
            
            if not org_users or not org_accounts:
                continue
            
            # Create 20 journal entries per org
            for i in range(20):
                entry_date = timezone.now() - timedelta(days=random.randint(0, 90))
                amount = Decimal(random.randint(5000, 50000))
                
                je = JournalEntry.objects.create(
                    organization=org,
                    entry_number=f"JE-{org.country}-{i+1:04d}",
                    entry_date=entry_date,
                    description=f"Journal Entry #{i+1}",
                    status='posted' if random.random() < 0.8 else 'draft',
                    total_debit=amount,
                    total_credit=amount,
                    is_balanced=True,
                    created_by=random.choice(org_users),
                    posted_by=random.choice(org_users) if random.random() < 0.8 else None,
                    posted_at=entry_date if random.random() < 0.8 else None,
                )
                
                # Create debit line
                JournalEntryLine.objects.create(
                    journal_entry=je,
                    account=org_accounts.get('1100'),  # AR
                    description='Debit - Accounts Receivable',
                    debit_amount=amount,
                    credit_amount=Decimal('0'),
                )
                
                # Create credit line
                JournalEntryLine.objects.create(
                    journal_entry=je,
                    account=org_accounts.get('4000'),  # Sales
                    description='Credit - Sales Revenue',
                    debit_amount=Decimal('0'),
                    credit_amount=amount,
                )
            
            self.stdout.write(f'  Created 20 journal entries for {org.name}')

    def create_compliance_checks(self, orgs, users, transactions):
        """Create compliance check records"""
        self.stdout.write('Creating compliance checks...')
        
        check_templates = [
            ('vat', 'VAT Registration Verification', 'medium'),
            ('vat', 'VAT Return Accuracy', 'high'),
            ('zatca', 'E-Invoice Format Compliance', 'high'),
            ('shariah', 'Interest-Free Transaction Check', 'medium'),
            ('ifrs', 'Revenue Recognition Standard', 'medium'),
            ('aml', 'Large Transaction Monitoring', 'critical'),
        ]
        
        for org in orgs:
            org_users = users.get(org.id, [])
            org_txns = transactions.get(org.id, [])
            
            if not org_users:
                continue
            
            # Create checks for each template
            for check_type, check_name, severity in check_templates:
                # Some pass, some fail
                status = random.choice(['passed', 'passed', 'passed', 'failed', 'warning'])
                
                related_txn = random.choice(org_txns) if org_txns else None
                
                ComplianceCheck.objects.create(
                    organization=org,
                    check_type=check_type,
                    check_name=check_name,
                    description=f"Compliance check for {check_name} - {org.name}",
                    status=status,
                    severity=severity,
                    compliance_score=random.randint(60, 100) if status != 'failed' else random.randint(20, 50),
                    related_entity_type='transaction' if related_txn else None,
                    related_entity_id=related_txn.id if related_txn else None,
                    violation_details={'details': f'Check performed on {timezone.now().date()}'} if status == 'failed' else None,
                    recommendation='Review and correct the identified issues' if status == 'failed' else None,
                    is_resolved=status != 'failed' or random.random() < 0.3,
                    checked_by=random.choice(org_users),
                )
            
            self.stdout.write(f'  Created {len(check_templates)} compliance checks for {org.name}')

    def create_audit_flags(self, orgs, users, transactions):
        """Create audit flags for anomalous transactions"""
        self.stdout.write('Creating audit flags...')
        
        for org in orgs:
            org_users = users.get(org.id, [])
            org_txns = transactions.get(org.id, [])
            
            # Get anomalous transactions
            anomalous_txns = [t for t in org_txns if t.is_anomaly]
            
            flag_count = 0
            for txn in anomalous_txns:
                flag_type = txn.anomaly_type or 'manual_review'
                
                AuditFlag.objects.create(
                    organization=org,
                    transaction=txn,
                    flag_type=flag_type,
                    priority='high' if flag_type in ['fraud_risk', 'duplicate'] else 'medium',
                    title=f'{flag_type.replace("_", " ").title()} - {txn.reference_number}',
                    description=f'AI detected potential {flag_type.replace("_", " ")} in transaction {txn.reference_number}',
                    details_json={
                        'amount': str(txn.amount),
                        'vendor': txn.vendor_customer,
                        'date': str(txn.transaction_date.date()),
                    },
                    is_ai_detected=True,
                    confidence_score=random.randint(70, 95),
                    is_resolved=random.random() < 0.3,
                    resolved_by=random.choice(org_users) if random.random() < 0.3 else None,
                )
                flag_count += 1
            
            # Add some random compliance flags
            for _ in range(5):
                if org_txns:
                    txn = random.choice(org_txns)
                    AuditFlag.objects.create(
                        organization=org,
                        transaction=txn,
                        flag_type='vat_error',
                        priority='medium',
                        title=f'VAT Calculation Review - {txn.reference_number}',
                        description='VAT amount may need verification',
                        is_ai_detected=True,
                        confidence_score=random.randint(60, 85),
                    )
                    flag_count += 1
            
            self.stdout.write(f'  Created {flag_count} audit flags for {org.name}')

    def create_insights(self, orgs):
        """Create AI-generated insights"""
        self.stdout.write('Creating insights...')
        
        insight_templates = [
            ('trend', 'high', 'Revenue Growth Opportunity', 'Analysis shows potential for 15% revenue increase through seasonal pricing optimization'),
            ('anomaly', 'critical', 'Unusual Transaction Pattern', 'Detected cluster of high-value transactions requiring review'),
            ('recommendation', 'medium', 'Cost Reduction Suggestion', 'Switching suppliers could reduce COGS by 8%'),
            ('prediction', 'medium', 'Cash Flow Warning', 'Predicted cash shortfall in 60 days based on current AR aging'),
            ('alert', 'high', 'Compliance Deadline', 'VAT return due in 15 days - review pending transactions'),
        ]
        
        for org in orgs:
            for insight_type, severity, title, description in insight_templates:
                Insight.objects.create(
                    organization=org,
                    insight_type=insight_type,
                    severity=severity,
                    title=title,
                    description=description,
                    is_resolved=random.random() < 0.2,
                )
            
            self.stdout.write(f'  Created {len(insight_templates)} insights for {org.name}')

    def create_reports(self, orgs, users):
        """Create sample reports"""
        self.stdout.write('Creating reports...')
        
        report_types = ['income_statement', 'balance_sheet', 'cash_flow', 'vat_return']
        
        for org in orgs:
            org_users = users.get(org.id, [])
            if not org_users:
                continue
            
            for report_type in report_types:
                period_end = timezone.now()
                period_start = period_end - timedelta(days=30)
                
                Report.objects.create(
                    organization=org,
                    report_type=report_type,
                    report_name=f'{report_type.replace("_", " ").title()} - {period_end.strftime("%B %Y")}',
                    period_start=period_start,
                    period_end=period_end,
                    status=random.choice(['generated', 'reviewed', 'approved']),
                    data_json={
                        'generated_at': str(timezone.now()),
                        'period': f'{period_start.date()} to {period_end.date()}',
                    },
                    generated_by=random.choice(org_users),
                )
            
            self.stdout.write(f'  Created {len(report_types)} reports for {org.name}')

    def create_audit_logs(self, orgs, users):
        """Create audit log entries"""
        self.stdout.write('Creating audit logs...')
        
        actions = [
            'user_login', 'document_upload', 'transaction_create',
            'report_generate', 'compliance_check', 'data_export'
        ]
        
        for org in orgs:
            org_users = users.get(org.id, [])
            if not org_users:
                continue
            
            for _ in range(30):
                user = random.choice(org_users)
                action = random.choice(actions)
                
                AuditLog.objects.create(
                    organization=org,
                    user=user,
                    action=action,
                    entity_type='system',
                    ip_address=f'192.168.{random.randint(1,255)}.{random.randint(1,255)}',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                )
            
            self.stdout.write(f'  Created 30 audit logs for {org.name}')

    def print_summary(self):
        """Print summary of seeded data"""
        self.stdout.write('\n=== DATA SUMMARY ===')
        self.stdout.write(f'Organizations: {Organization.objects.count()}')
        self.stdout.write(f'Users: {User.objects.count()}')
        self.stdout.write(f'Accounts: {Account.objects.count()}')
        self.stdout.write(f'Transactions: {Transaction.objects.count()}')
        self.stdout.write(f'  - Anomalous: {Transaction.objects.filter(is_anomaly=True).count()}')
        self.stdout.write(f'Journal Entries: {JournalEntry.objects.count()}')
        self.stdout.write(f'Compliance Checks: {ComplianceCheck.objects.count()}')
        self.stdout.write(f'Audit Flags: {AuditFlag.objects.count()}')
        self.stdout.write(f'Insights: {Insight.objects.count()}')
        self.stdout.write(f'Reports: {Report.objects.count()}')
        self.stdout.write(f'Audit Logs: {AuditLog.objects.count()}')
