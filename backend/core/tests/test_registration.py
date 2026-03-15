from django.contrib.auth import SESSION_KEY, get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Organization, OrganizationMember
from core.serializers import UserSerializer

User = get_user_model()


class UserCreationWithOrganizationTests(TestCase):
    def test_create_user_without_organization_provisions_owner_membership(self):
        user = User.objects.create_user(
            email='placeholder@example.com',
            password='Sup3rSecurePass!2026',
            name='Placeholder User',
        )

        membership = OrganizationMember.objects.get(user=user, organization=user.organization)

        self.assertTrue(user.check_password('Sup3rSecurePass!2026'))
        self.assertEqual(user.role, 'admin')
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.created_by, user)
        self.assertEqual(user.organization.country, 'AE')
        self.assertEqual(user.organization.currency, 'AED')
        self.assertEqual(user.organization.vat_validation_status, 'not_required')
        self.assertEqual(membership.role, 'owner')
        self.assertTrue(user.organization.name.endswith('Organization'))

    def test_create_user_with_existing_organization_creates_membership(self):
        organization = Organization.objects.create(
            name='Real Company',
            name_ar='Real Company',
            country='SA',
        )

        user = User.objects.create_user(
            email='real@example.com',
            password='Sup3rSecurePass!2026',
            name='Real User',
            role='auditor',
            organization=organization,
        )

        membership = OrganizationMember.objects.get(user=user, organization=organization)

        self.assertEqual(user.organization, organization)
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(membership.role, 'member')
        self.assertEqual(user.role, 'auditor')

    def test_user_serializer_create_provisions_owner_membership(self):
        serializer = UserSerializer(data={
            'email': 'serializer@example.com',
            'name': 'Serializer User',
            'password': 'Sup3rSecurePass!2026',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        membership = OrganizationMember.objects.get(user=user, organization=user.organization)

        self.assertTrue(user.check_password('Sup3rSecurePass!2026'))
        self.assertEqual(user.role, 'admin')
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.created_by, user)
        self.assertEqual(membership.role, 'owner')


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.dashboard_url = reverse('dashboard')

    def test_register_view_logs_user_in_and_creates_owner_membership(self):
        response = self.client.post(self.register_url, {
            'full_name': 'Register User',
            'email': 'register@example.com',
            'password': 'Sup3rSecurePass!2026',
            'password_confirm': 'Sup3rSecurePass!2026',
        })

        user = User.objects.get(email='register@example.com')
        membership = OrganizationMember.objects.get(user=user, organization=user.organization)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.dashboard_url)
        self.assertIn(SESSION_KEY, self.client.session)
        self.assertEqual(user.role, 'admin')
        self.assertEqual(user.organization.created_by, user)
        self.assertEqual(membership.role, 'owner')

    def test_register_view_uses_submitted_company_details_when_available(self):
        response = self.client.post(self.register_url, {
            'full_name': 'Company Admin',
            'email': 'company-admin@example.com',
            'password': 'Sup3rSecurePass!2026',
            'password_confirm': 'Sup3rSecurePass!2026',
            'company_name': 'Real Company',
            'tax_number': '1234567890',
        })

        user = User.objects.get(email='company-admin@example.com')
        membership = OrganizationMember.objects.get(user=user, organization=user.organization)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.dashboard_url)
        self.assertEqual(user.organization.name, 'Real Company')
        self.assertEqual(user.organization.vat_number, '1234567890')
        self.assertEqual(user.organization.created_by, user)
        self.assertEqual(membership.role, 'owner')

    def test_login_view_backfills_organization_for_legacy_user_without_organization(self):
        legacy_user = User(
            email='legacy@example.com',
            name='Legacy User',
            role='user',
            social_provider='email',
            login_method='email',
        )
        legacy_user.set_password('Sup3rSecurePass!2026')
        legacy_user.save()

        response = self.client.post(self.login_url, {
            'email': 'legacy@example.com',
            'password': 'Sup3rSecurePass!2026',
        })

        legacy_user.refresh_from_db()
        membership = OrganizationMember.objects.get(user=legacy_user, organization=legacy_user.organization)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.dashboard_url)
        self.assertEqual(legacy_user.role, 'admin')
        self.assertIsNotNone(legacy_user.organization)
        self.assertEqual(legacy_user.organization.created_by, legacy_user)
        self.assertEqual(membership.role, 'owner')

    def test_legacy_accounts_register_url_redirects_to_register(self):
        response = self.client.get('/accounts/register/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.register_url)

    def test_legacy_accounts_login_url_redirects_to_login(self):
        response = self.client.get('/accounts/login/')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)
