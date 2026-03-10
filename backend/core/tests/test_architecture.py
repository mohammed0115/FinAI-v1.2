from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse
from rest_framework.test import APIClient

from core.models import Configuration, Organization
from core.views.auth_views import LoginPageView
from core.views.dashboard_views import DashboardPageView
from core.views.document_page_views import DocumentUploadPageView, PendingReviewSubmitView

User = get_user_model()


class PresentationArchitectureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org_a = Organization.objects.create(name='Org A', country='SA', currency='SAR')
        cls.org_b = Organization.objects.create(name='Org B', country='AE', currency='AED')

        cls.org_a_user = User.objects.create_user(
            email='user-a@example.com',
            password='StrongPass!123',
            name='User A',
            role='user',
            organization=cls.org_a,
            organization_member_role='member',
        )
        cls.org_a_peer = User.objects.create_user(
            email='peer-a@example.com',
            password='StrongPass!123',
            name='Peer A',
            role='accountant',
            organization=cls.org_a,
            organization_member_role='member',
        )
        cls.org_b_user = User.objects.create_user(
            email='user-b@example.com',
            password='StrongPass!123',
            name='User B',
            role='user',
            organization=cls.org_b,
            organization_member_role='member',
        )

    def test_login_route_uses_class_based_view(self):
        match = resolve(reverse('login'))
        self.assertIs(match.func.view_class, LoginPageView)

    def test_dashboard_route_uses_class_based_view(self):
        match = resolve(reverse('dashboard'))
        self.assertIs(match.func.view_class, DashboardPageView)

    def test_document_routes_use_class_based_views(self):
        upload_match = resolve(reverse('document_upload'))
        submit_match = resolve(reverse('pending_review_submit', kwargs={'document_id': self.org_a.id}))

        self.assertIs(upload_match.func.view_class, DocumentUploadPageView)
        self.assertIs(submit_match.func.view_class, PendingReviewSubmitView)

    def test_user_api_is_tenant_scoped_for_non_admin(self):
        client = APIClient()
        client.force_authenticate(user=self.org_a_user)
        response = client.get(reverse('user-list'))

        payload = response.json()
        records = payload['results'] if isinstance(payload, dict) and 'results' in payload else payload
        returned_emails = {item['email'] for item in records}
        self.assertIn(self.org_a_user.email, returned_emails)
        self.assertIn(self.org_a_peer.email, returned_emails)
        self.assertNotIn(self.org_b_user.email, returned_emails)

    def test_configuration_api_auto_assigns_organization_and_actor(self):
        client = APIClient()
        client.force_authenticate(user=self.org_a_user)
        response = client.post(
            reverse('configuration-list'),
            {
                'config_key': 'dashboard.refresh_interval',
                'config_value': '30',
                'config_type': 'organization',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.json())
        config = Configuration.objects.get(config_key='dashboard.refresh_interval', organization=self.org_a)
        self.assertEqual(config.updated_by, self.org_a_user)
