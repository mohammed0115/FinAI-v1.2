from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from core.models import Organization
from core.serializers import UserSerializer

User = get_user_model()


class UserCreationWithOrganizationTests(TestCase):
    def test_create_user_without_organization_creates_placeholder_organization(self):
        user = User.objects.create_user(
            email='placeholder@example.com',
            password='Sup3rSecurePass!2026',
            name='Placeholder User',
        )

        self.assertTrue(user.check_password('Sup3rSecurePass!2026'))
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')
        self.assertEqual(user.organization.currency, 'AED')
        self.assertEqual(user.organization.vat_validation_status, 'not_required')
        self.assertIn('Placeholder Company', user.organization.name)

    def test_create_user_with_existing_organization_keeps_it(self):
        organization = Organization.objects.create(
            name='Real Company',
            name_ar='Real Company',
            country='SA',
        )

        user = User.objects.create_user(
            email='real@example.com',
            password='Sup3rSecurePass!2026',
            name='Real User',
            organization=organization,
        )

        self.assertEqual(user.organization, organization)
        self.assertEqual(Organization.objects.count(), 1)

    def test_user_serializer_create_uses_placeholder_organization(self):
        serializer = UserSerializer(data={
            'email': 'serializer@example.com',
            'name': 'Serializer User',
            'password': 'Sup3rSecurePass!2026',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertTrue(user.check_password('Sup3rSecurePass!2026'))
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')

    def test_register_view_creates_placeholder_organization(self):
        response = self.client.post(self.register_url, {
            'full_name': 'Register User',
            'email': 'register@example.com',
            'password': 'Sup3rSecurePass!2026',
            'password_confirm': 'Sup3rSecurePass!2026',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

        user = User.objects.get(email='register@example.com')
        self.assertEqual(user.role, 'admin')
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')
        self.assertEqual(Organization.objects.count(), 1)

    def test_register_view_uses_submitted_company_details_when_available(self):
        response = self.client.post(self.register_url, {
            'full_name': 'Company Admin',
            'email': 'company-admin@example.com',
            'password': 'Sup3rSecurePass!2026',
            'password_confirm': 'Sup3rSecurePass!2026',
            'company_name': 'Real Company',
            'tax_number': '1234567890',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.login_url)

        user = User.objects.get(email='company-admin@example.com')
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.name, 'Real Company')
        self.assertEqual(user.organization.country, 'SA')
        self.assertEqual(user.organization.vat_number, '1234567890')
