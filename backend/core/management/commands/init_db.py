"""
Management command to initialize the database for production deployment.
This creates the superuser and test data if they don't exist.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import User, Organization
from django.utils import timezone


class Command(BaseCommand):
    help = 'Initialize database with default admin user and organization'

    def handle(self, *args, **options):
        self.stdout.write('Starting database initialization...')
        
        try:
            with transaction.atomic():
                # Check if admin user already exists
                if User.objects.filter(email='admin@finai.com').exists():
                    self.stdout.write(self.style.WARNING('Admin user already exists, skipping initialization'))
                    return
                
                # Create organization
                org, created = Organization.objects.get_or_create(
                    name="FinAI Demo Company",
                    defaults={
                        'country': 'SA',
                        'tax_id': '123456789',
                        'vat_rate': 15,
                        'currency': 'SAR',
                        'industry': 'Financial Services',
                        'company_type': 'private'
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Created organization: {org.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Organization already exists: {org.name}'))
                
                # Create superuser
                admin = User.objects.create_superuser(
                    email='admin@finai.com',
                    password='admin123',
                    name='Admin User'
                )
                admin.organization = org
                admin.save()
                self.stdout.write(self.style.SUCCESS('✓ Created admin user: admin@finai.com / admin123'))
                
                # Create test accountant
                accountant = User.objects.create_user(
                    email='accountant@finai.com',
                    password='accountant123',
                    name='Test Accountant',
                    role='accountant'
                )
                accountant.organization = org
                accountant.save()
                self.stdout.write(self.style.SUCCESS('✓ Created accountant: accountant@finai.com / accountant123'))
                
                self.stdout.write(self.style.SUCCESS('\n=== Database initialization complete ==='))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during initialization: {str(e)}'))
            raise
