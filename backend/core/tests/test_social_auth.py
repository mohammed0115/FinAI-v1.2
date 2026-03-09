"""
Social Authentication Tests
============================
Tests for Google & Facebook OAuth2 integration

Run tests:
    python manage.py test core.tests.test_social_auth --verbosity=2
"""

import json
from unittest.mock import patch, Mock

from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings

User = get_user_model()


@override_settings(
    GOOGLE_CLIENT_ID='dummy_client_id',
    GOOGLE_CLIENT_SECRET='dummy_client_secret',
)
class GoogleOAuthTestCase(TestCase):
    """Tests for Google OAuth2 flow"""
    
    def setUp(self):
        self.client = Client()
        self.google_login_url = reverse('google_login')
        self.google_callback_url = reverse('google_callback')
    
    def test_google_login_redirect(self):
        """Test that google_login redirects to Google OAuth URL"""
        response = self.client.get(self.google_login_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.url)
        self.assertIn('client_id', response.url)
        self.assertIn('redirect_uri', response.url)
        self.assertIn('state', response.url)
    
    def test_google_login_missing_credentials(self):
        """Test google_login when credentials not configured"""
        with patch.object(settings, 'GOOGLE_CLIENT_ID', ''):
            response = self.client.get(self.google_login_url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('login'))
    
    def test_google_callback_csrf_state_failure(self):
        """Test google_callback with mismatched CSRF state"""
        response = self.client.get(self.google_callback_url, {
            'code': 'auth_code_123',
            'state': 'invalid_state',
        })
        
        # Should redirect to login due to CSRF failure
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
    
    @patch('core.social_auth_views.http_requests.post')
    @patch('core.social_auth_views.http_requests.get')
    def test_google_callback_success_new_user(self, mock_get, mock_post):
        """Test successful Google callback creating new user"""
        # Setup session state
        self.client.get(self.google_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange
        mock_post.return_value = Mock(
            json=lambda: {
                'access_token': 'access_token_123',
                'token_type': 'Bearer',
                'expires_in': 3599,
            },
            raise_for_status=lambda: None,
        )
        
        # Mock profile fetch
        mock_get.return_value = Mock(
            json=lambda: {
                'id': 'google_123456',
                'email': 'newuser@gmail.com',
                'name': 'New User',
            },
            raise_for_status=lambda: None,
        )
        
        # Simulate callback
        response = self.client.get(self.google_callback_url, {
            'code': 'auth_code_123',
            'state': state_token,
        }, follow=True)
        
        # Check user was created
        user = User.objects.get(email='newuser@gmail.com')
        self.assertEqual(user.google_id, 'google_123456')
        self.assertEqual(user.social_provider, 'google')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')
    
    @patch('core.social_auth_views.http_requests.post')
    @patch('core.social_auth_views.http_requests.get')
    def test_google_callback_success_existing_user(self, mock_get, mock_post):
        """Test successful Google callback linking to existing user"""
        # Create existing user
        existing_user = User.objects.create_user(
            email='existing@gmail.com',
            name='Existing User',
        )
        
        # Setup session state
        self.client.get(self.google_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange
        mock_post.return_value = Mock(
            json=lambda: {
                'access_token': 'access_token_456',
            },
            raise_for_status=lambda: None,
        )
        
        # Mock profile fetch with same email
        mock_get.return_value = Mock(
            json=lambda: {
                'id': 'google_654321',
                'email': 'existing@gmail.com',
                'name': 'Existing User',
            },
            raise_for_status=lambda: None,
        )
        
        # Simulate callback
        response = self.client.get(self.google_callback_url, {
            'code': 'auth_code_456',
            'state': state_token,
        }, follow=True)
        
        # Check user was linked
        user = User.objects.get(email='existing@gmail.com')
        self.assertEqual(user.google_id, 'google_654321')
        self.assertEqual(user.social_provider, 'google')
    
    @patch('core.social_auth_views.http_requests.post')
    def test_google_callback_token_exchange_failure(self, mock_post):
        """Test google_callback when token exchange fails"""
        # Setup session state
        self.client.get(self.google_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange failure with RequestException
        from requests.exceptions import RequestException
        mock_post.side_effect = RequestException('Network error')
        
        # Simulate callback
        response = self.client.get(self.google_callback_url, {
            'code': 'auth_code_789',
            'state': state_token,
        })
        
        # Should redirect to login with error message
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
    
    def test_google_callback_missing_code(self):
        """Test google_callback without auth code"""
        # Setup session state
        self.client.get(self.google_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Simulate callback without code
        response = self.client.get(self.google_callback_url, {
            'state': state_token,
            'error': 'access_denied',
        })
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))


@override_settings(
    FACEBOOK_LOGIN_ENABLED=True,
    FACEBOOK_APP_ID='dummy_facebook_app_id',
    FACEBOOK_APP_SECRET='dummy_facebook_app_secret',
)
class FacebookOAuthTestCase(TestCase):
    """Tests for Facebook OAuth2 flow"""
    
    def setUp(self):
        self.client = Client()
        self.facebook_login_url = reverse('facebook_login')
        self.facebook_callback_url = reverse('facebook_callback')
    
    def test_facebook_login_redirect(self):
        """Test that facebook_login redirects to Facebook OAuth URL"""
        response = self.client.get(self.facebook_login_url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('facebook.com', response.url)
        self.assertIn('client_id', response.url)
        self.assertIn('redirect_uri', response.url)
        self.assertIn('state', response.url)
    
    def test_facebook_login_missing_credentials(self):
        """Test facebook_login when credentials not configured"""
        with patch.object(settings, 'FACEBOOK_APP_ID', ''):
            response = self.client.get(self.facebook_login_url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse('login'))
    
    def test_facebook_callback_csrf_state_failure(self):
        """Test facebook_callback with mismatched CSRF state"""
        response = self.client.get(self.facebook_callback_url, {
            'code': 'auth_code_fb',
            'state': 'invalid_state',
        })
        
        # Should redirect to login due to CSRF failure
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))
    
    @patch('core.social_auth_views.http_requests.get')
    def test_facebook_callback_success_new_user(self, mock_get):
        """Test successful Facebook callback creating new user"""
        # Setup session state
        self.client.get(self.facebook_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange (first get call)
        # Mock profile fetch (second get call)
        mock_get.side_effect = [
            Mock(
                json=lambda: {
                    'access_token': 'fb_access_token_123',
                },
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {
                    'id': '987654321',
                    'email': 'newuser@facebook.com',
                    'name': 'New Facebook User',
                },
                raise_for_status=lambda: None,
            ),
        ]
        
        # Simulate callback
        response = self.client.get(self.facebook_callback_url, {
            'code': 'auth_code_fb',
            'state': state_token,
        }, follow=True)
        
        # Check user was created
        user = User.objects.get(email='newuser@facebook.com')
        self.assertEqual(user.facebook_id, '987654321')
        self.assertEqual(user.social_provider, 'facebook')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')
    
    @patch('core.social_auth_views.http_requests.get')
    def test_facebook_callback_success_existing_user(self, mock_get):
        """Test successful Facebook callback linking to existing user"""
        # Create existing user
        existing_user = User.objects.create_user(
            email='existing_fb@email.com',
            name='Existing FB User',
        )
        
        # Setup session state
        self.client.get(self.facebook_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange and profile fetch
        mock_get.side_effect = [
            Mock(
                json=lambda: {
                    'access_token': 'fb_access_token_456',
                },
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {
                    'id': '123456789',
                    'email': 'existing_fb@email.com',
                    'name': 'Existing FB User',
                },
                raise_for_status=lambda: None,
            ),
        ]
        
        # Simulate callback
        response = self.client.get(self.facebook_callback_url, {
            'code': 'auth_code_fb_existing',
            'state': state_token,
        }, follow=True)
        
        # Check user was linked
        user = User.objects.get(email='existing_fb@email.com')
        self.assertEqual(user.facebook_id, '123456789')
        self.assertEqual(user.social_provider, 'facebook')
    
    @patch('core.social_auth_views.http_requests.get')
    def test_facebook_callback_missing_email(self, mock_get):
        """Test Facebook callback when profile has no email"""
        # Setup session state
        self.client.get(self.facebook_login_url)
        session = self.client.session
        state_token = session.get('oauth_state')
        
        # Mock token exchange and profile without email
        mock_get.side_effect = [
            Mock(
                json=lambda: {
                    'access_token': 'fb_access_token_no_email',
                },
                raise_for_status=lambda: None,
            ),
            Mock(
                json=lambda: {
                    'id': '111111111',
                    'name': 'User Without Email',
                },
                raise_for_status=lambda: None,
            ),
        ]
        
        # Simulate callback
        response = self.client.get(self.facebook_callback_url, {
            'code': 'auth_code_no_email',
            'state': state_token,
        })
        
        # Should redirect to login (no email = can't create user)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))


class UserCreationTestCase(TestCase):
    """Tests for social user creation logic"""
    
    def test_get_or_create_new_user_google(self):
        """Test creating new user from Google data"""
        from core.social_auth_views import _get_or_create_social_user
        
        user = _get_or_create_social_user(
            email='newgoogleuser@gmail.com',
            name='New Google User',
            provider='google',
            provider_id='google_new_123',
        )
        
        self.assertEqual(user.email, 'newgoogleuser@gmail.com')
        self.assertEqual(user.google_id, 'google_new_123')
        self.assertEqual(user.social_provider, 'google')
        self.assertTrue(user.is_active)
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.country, 'AE')
    
    def test_get_or_create_existing_user_link(self):
        """Test linking social ID to existing user"""
        from core.social_auth_views import _get_or_create_social_user
        
        # Create user first
        existing = User.objects.create_user(
            email='linking@email.com',
            name='Link Test'
        )
        
        # Now link social ID
        user = _get_or_create_social_user(
            email='linking@email.com',
            name='Link Test',
            provider='google',
            provider_id='google_link_123',
        )
        
        self.assertEqual(user.id, existing.id)
        self.assertEqual(user.google_id, 'google_link_123')
    
    def test_get_or_create_provider_id_lookup(self):
        """Test looking up user by provider ID"""
        from core.social_auth_views import _get_or_create_social_user
        
        # Create user with provider ID
        user1 = _get_or_create_social_user(
            email='provider@email.com',
            name='Provider Test',
            provider='facebook',
            provider_id='fb_existing_123',
        )
        
        # Try to get same user by provider ID
        user2 = _get_or_create_social_user(
            email='different@email.com',  # Different email
            name='Different Name',
            provider='facebook',
            provider_id='fb_existing_123',  # Same provider ID
        )
        
        # Should return same user (matched by provider_id)
        self.assertEqual(user1.id, user2.id)
    
    def test_get_or_create_missing_email(self):
        """Test error handling when email is missing"""
        from core.social_auth_views import _get_or_create_social_user
        
        with self.assertRaises(ValueError) as context:
            _get_or_create_social_user(
                email='',
                name='No Email User',
                provider='google',
                provider_id='google_no_email',
            )
        
        self.assertIn('email', str(context.exception).lower())
    
    def test_get_or_create_missing_provider_id(self):
        """Test error handling when provider_id is missing"""
        from core.social_auth_views import _get_or_create_social_user
        
        with self.assertRaises(ValueError) as context:
            _get_or_create_social_user(
                email='test@email.com',
                name='Test User',
                provider='google',
                provider_id='',
            )
        
        self.assertIn('id', str(context.exception).lower())


@override_settings(
    GOOGLE_CLIENT_ID='dummy_client_id',
    GOOGLE_CLIENT_SECRET='dummy_client_secret',
    FACEBOOK_LOGIN_ENABLED=True,
    FACEBOOK_APP_ID='dummy_facebook_app_id',
    FACEBOOK_APP_SECRET='dummy_facebook_app_secret',
)
class SessionSecurityTestCase(TestCase):
    """Tests for session and CSRF security"""
    
    def test_oauth_state_stored_in_session(self):
        """Test that OAuth state is stored in session"""
        self.client.get(reverse('google_login'))
        
        session = self.client.session
        self.assertIn('oauth_state', session)
        self.assertEqual(len(session['oauth_state']), 43)  # base64 encoded
    
    def test_oauth_state_varies(self):
        """Test that each OAuth request gets a different state"""
        self.client.get(reverse('google_login'))
        state1 = self.client.session.get('oauth_state')
        
        # Need new client or session
        client2 = Client()
        client2.get(reverse('facebook_login'))
        state2 = client2.session.get('oauth_state')
        
        self.assertNotEqual(state1, state2)
    
    def test_csrf_protection_different_sessions(self):
        """Test CSRF protection prevents cross-session attacks"""
        # Session 1 starts OAuth flow
        self.client.get(reverse('google_login'))
        state1 = self.client.session.get('oauth_state')
        
        # Session 2 tries to use state from Session 1
        response = self.client.get(reverse('google_callback'), {
            'code': 'attack_code',
            'state': 'wrong_state_token',
        })
        
        # Should reject due to state mismatch
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('login'))


# Integration test command:
# python manage.py test core.tests.test_social_auth --verbosity=2
#
# To run specific test:
# python manage.py test core.tests.test_social_auth.GoogleOAuthTestCase.test_google_login_redirect
#
# To run with coverage:
# coverage run --source='core' manage.py test core.tests.test_social_auth
# coverage report
