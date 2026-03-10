"""
Social Login Views — Google & Facebook OAuth2
=============================================
Flow:
    1. User clicks "Continue with Google/Facebook"
    2. Redirect to provider's OAuth consent page
    3. Provider redirects back to our callback URL with ?code=...
    4. Exchange code for access token
    5. Fetch user profile from provider
    6. Create or link account, then log user in
"""

import logging
import secrets
import urllib.parse

import requests as http_requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse

from .models import User

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers

def _resolve_redirect_uri(request, provider, callback_view_name):
    """
    Resolve OAuth redirect URI for a provider.

    Priority:
      1) <PROVIDER>_REDIRECT_URI from settings (e.g., GOOGLE_REDIRECT_URI)
      2) request.build_absolute_uri(reverse(callback_view_name))
    """
    override = getattr(settings, f'{provider.upper()}_REDIRECT_URI', '')
    if override:
        return override
    return request.build_absolute_uri(reverse(callback_view_name))
# ─────────────────────────────────────────────────────────────────────────────

def _get_or_create_social_user(email, name, provider, provider_id):
    """
    Find existing user by provider_id or email, then create/link as needed.
    
    Args:
        email: User email from OAuth provider
        name: User name from OAuth provider
        provider: 'google' or 'facebook'
        provider_id: Unique ID from OAuth provider
        
    Returns:
        User instance
        
    Raises:
        ValueError: If email is missing
    """
    if not provider_id:
        raise ValueError(f'No {provider} ID returned from provider')
        
    if not email:
        raise ValueError('No email returned from provider — cannot create account')

    # 1. Try to find by provider-specific ID (highest priority)
    filter_kwargs = {f'{provider}_id': provider_id}
    user = User.objects.filter(**filter_kwargs).first()
    if user:
        logger.info(f'Found existing user {user.email} by {provider}_id')
        User.objects.ensure_organization_setup(user, organization_name=name)
        return user

    # 2. Try to find by email (link existing account)
    user = User.objects.filter(email=email).first()
    if user:
        logger.info(f'Linking {provider} account to existing user {user.email}')
        setattr(user, f'{provider}_id', provider_id)
        if not user.social_provider:
            user.social_provider = provider
        if not user.login_method:
            user.login_method = provider
        user.save(update_fields=[f'{provider}_id', 'social_provider', 'login_method'])
        User.objects.ensure_organization_setup(user, organization_name=name)
        return user

    # 3. Create new account
    logger.info(f'Creating new user account from {provider} login: {email}')
    user = User.objects.create_user(
        email=email,
        password=None,  # unusable password — social-only account
        name=name or email.split('@')[0],
        role='admin',
        social_provider=provider,
        login_method=provider,
        is_active=True,
        organization_name=name,
        organization_member_role='owner',
    )
    setattr(user, f'{provider}_id', provider_id)
    user.save(update_fields=[f'{provider}_id'])
    
    logger.info(f'New user created: {user.email} via {provider}')
    return user


# ─────────────────────────────────────────────────────────────────────────────
#  Google OAuth2
# ─────────────────────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v2/userinfo'
GOOGLE_SCOPES = 'openid email profile'


def google_login(request):
    """Redirect user to Google's OAuth consent page."""
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    if not client_id:
        logger.warning('Google login attempted but GOOGLE_CLIENT_ID not configured')
        messages.error(request, 'خدمة Google OAuth غير مكوّنة. يرجى التواصل مع الدعم')
        return redirect('login')

    # Store random state in session to prevent CSRF
    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    request.session.set_expiry(600)  # State expires in 10 minutes

    callback_url = _resolve_redirect_uri(request, 'google', 'google_callback')
    request.session['google_oauth_redirect_uri'] = callback_url

    params = {
        'client_id': client_id,
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': GOOGLE_SCOPES,
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    url = GOOGLE_AUTH_URL + '?' + urllib.parse.urlencode(params)
    logger.info(f'Redirecting to Google OAuth: {callback_url}')
    return redirect(url)


def google_callback(request):
    """Handle Google's OAuth callback."""
    # CSRF state check
    state = request.GET.get('state')
    session_state = request.session.pop('oauth_state', None)
    
    if not state or state != session_state:
        logger.warning('CSRF state validation failed for Google OAuth')
        messages.error(request, 'تحقق الأمان فشل. يرجى المحاولة مجدداً')
        return redirect('login')

    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error', 'Unknown error')
        error_desc = request.GET.get('error_description', '')
        logger.warning(f'Google login cancelled: {error} - {error_desc}')
        messages.error(request, 'تم إلغاء تسجيل الدخول عبر Google')
        return redirect('login')

    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_CLIENT_SECRET', '')
    
    if not client_id or not client_secret:
        logger.error('Google OAuth credentials not configured')
        messages.error(request, 'خدمة Google OAuth غير مكوّنة. يرجى التواصل مع الدعم')
        return redirect('login')
    
    callback_url = request.session.pop('google_oauth_redirect_uri', None)
    if not callback_url:
        callback_url = _resolve_redirect_uri(request, 'google', 'google_callback')

    # Exchange code for token
    try:
        token_resp = http_requests.post(
            GOOGLE_TOKEN_URL,
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': callback_url,
                'grant_type': 'authorization_code',
            },
            timeout=10,
        )
        try:
            token_resp.raise_for_status()
        except http_requests.exceptions.HTTPError as exc:
            logger.error(
                'Google token exchange failed: %s | status=%s body=%s',
                exc, token_resp.status_code, token_resp.text,
            )
            messages.error(request, 'فشل تبادل البيانات مع Google. يرجى المحاولة مجدداً')
            return redirect('login')
        token_data = token_resp.json()
    except http_requests.exceptions.RequestException as exc:
        logger.error(f'Google token exchange failed: {exc}', exc_info=True)
        messages.error(request, 'فشل تبادل البيانات مع Google. يرجى المحاولة مجدداً')
        return redirect('login')
    except ValueError as exc:
        logger.error(f'Invalid JSON response from Google: {exc}')
        messages.error(request, 'استجابة غير صحيحة من Google')
        return redirect('login')

    access_token = token_data.get('access_token')
    if not access_token:
        logger.warning('Google did not return an access token')
        messages.error(request, 'Google لم يعيد رمز الوصول (access token)')
        return redirect('login')

    # Fetch user profile
    try:
        profile_resp = http_requests.get(
            GOOGLE_USERINFO_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    except http_requests.exceptions.RequestException as exc:
        logger.error(f'Google profile fetch failed: {exc}', exc_info=True)
        messages.error(request, 'فشل جلب ملف Google. يرجى المحاولة مجدداً')
        return redirect('login')
    except ValueError as exc:
        logger.error(f'Invalid JSON in Google profile: {exc}')
        messages.error(request, 'استجابة غير صحيحة من Google')
        return redirect('login')

    google_id = profile.get('id')
    email = profile.get('email', '')
    name = profile.get('name', '')

    if not google_id:
        logger.warning(f'Google profile missing ID for email {email}')
        messages.error(request, 'معرّف Google غير متوفر')
        return redirect('login')

    try:
        user = _get_or_create_social_user(email, name, 'google', google_id)
    except ValueError as exc:
        logger.warning(f'Social user creation error: {exc}')
        messages.error(request, str(exc))
        return redirect('login')
    except Exception as exc:
        logger.error(f'Social user creation failed (Google): {exc}', exc_info=True)
        messages.error(request, 'فشل إعداد الحساب. يرجى التواصل مع الدعم')
        return redirect('login')

    # Log in the user
    try:
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info(f'User {user.email} logged in via Google')
        messages.success(request, f'مرحباً {user.name}! تم تسجيل الدخول بنجاح')
        return redirect('dashboard')
    except Exception as exc:
        logger.error(f'Login failed for user {user.email}: {exc}', exc_info=True)
        messages.error(request, 'فشل تسجيل الدخول. يرجى المحاولة مجدداً')
        return redirect('login')


# ─────────────────────────────────────────────────────────────────────────────
#  Facebook OAuth2
# ─────────────────────────────────────────────────────────────────────────────

FACEBOOK_AUTH_URL = 'https://www.facebook.com/v18.0/dialog/oauth'
FACEBOOK_TOKEN_URL = 'https://graph.facebook.com/v18.0/oauth/access_token'
FACEBOOK_USERINFO_URL = 'https://graph.facebook.com/me'
FACEBOOK_SCOPES = 'email,public_profile'


def facebook_login(request):
    """Redirect user to Facebook's OAuth consent page."""
    if not getattr(settings, 'FACEBOOK_LOGIN_ENABLED', False):
        logger.info('Facebook login disabled')
        messages.error(request, 'تسجيل الدخول عبر Facebook متوقف مؤقتًا')
        return redirect('login')

    app_id = getattr(settings, 'FACEBOOK_APP_ID', '')
    if not app_id:
        logger.warning('Facebook login attempted but FACEBOOK_APP_ID not configured')
        messages.error(request, 'خدمة Facebook OAuth غير مكوّنة. يرجى التواصل مع الدعم')
        return redirect('login')

    state = secrets.token_urlsafe(32)
    request.session['oauth_state'] = state
    request.session.set_expiry(600)  # State expires in 10 minutes

    callback_url = _resolve_redirect_uri(request, 'facebook', 'facebook_callback')
    request.session['facebook_oauth_redirect_uri'] = callback_url

    params = {
        'client_id': app_id,
        'redirect_uri': callback_url,
        'response_type': 'code',
        'scope': FACEBOOK_SCOPES,
        'state': state,
    }
    url = FACEBOOK_AUTH_URL + '?' + urllib.parse.urlencode(params)
    logger.info(f'Redirecting to Facebook OAuth: {callback_url}')
    return redirect(url)


def facebook_callback(request):
    """Handle Facebook's OAuth callback."""
    if not getattr(settings, 'FACEBOOK_LOGIN_ENABLED', False):
        logger.info('Facebook callback blocked because login is disabled')
        messages.error(request, 'تسجيل الدخول عبر Facebook متوقف مؤقتًا')
        return redirect('login')

    # CSRF state check
    state = request.GET.get('state')
    session_state = request.session.pop('oauth_state', None)
    
    if not state or state != session_state:
        logger.warning('CSRF state validation failed for Facebook OAuth')
        messages.error(request, 'تحقق الأمان فشل. يرجى المحاولة مجدداً')
        return redirect('login')

    code = request.GET.get('code')
    if not code:
        error = request.GET.get('error_reason', 'Unknown error')
        error_desc = request.GET.get('error_description', '')
        logger.warning(f'Facebook login cancelled: {error} - {error_desc}')
        messages.error(request, 'تم إلغاء تسجيل الدخول عبر Facebook')
        return redirect('login')

    app_id = getattr(settings, 'FACEBOOK_APP_ID', '')
    app_secret = getattr(settings, 'FACEBOOK_APP_SECRET', '')
    
    if not app_id or not app_secret:
        logger.error('Facebook OAuth credentials not configured')
        messages.error(request, 'خدمة Facebook OAuth غير مكوّنة. يرجى التواصل مع الدعم')
        return redirect('login')
    
    callback_url = request.session.pop('facebook_oauth_redirect_uri', None)
    if not callback_url:
        callback_url = _resolve_redirect_uri(request, 'facebook', 'facebook_callback')

    # Exchange code for token
    try:
        token_resp = http_requests.get(
            FACEBOOK_TOKEN_URL,
            params={
                'client_id': app_id,
                'client_secret': app_secret,
                'redirect_uri': callback_url,
                'code': code,
            },
            timeout=10,
        )
        try:
            token_resp.raise_for_status()
        except http_requests.exceptions.HTTPError as exc:
            logger.error(
                'Facebook token exchange failed: %s | status=%s body=%s',
                exc, token_resp.status_code, token_resp.text,
            )
            messages.error(request, 'فشل تبادل البيانات مع Facebook. يرجى المحاولة مجدداً')
            return redirect('login')
        token_data = token_resp.json()
    except http_requests.exceptions.RequestException as exc:
        logger.error(f'Facebook token exchange failed: {exc}', exc_info=True)
        messages.error(request, 'فشل تبادل البيانات مع Facebook. يرجى المحاولة مجدداً')
        return redirect('login')
    except ValueError as exc:
        logger.error(f'Invalid JSON response from Facebook: {exc}')
        messages.error(request, 'استجابة غير صحيحة من Facebook')
        return redirect('login')

    # Check for errors in response
    if 'error' in token_data:
        error_msg = token_data.get('error', {}).get('message', 'Unknown error')
        logger.warning(f'Facebook token error: {error_msg}')
        messages.error(request, f'خطأ من Facebook: {error_msg}')
        return redirect('login')

    access_token = token_data.get('access_token')
    if not access_token:
        logger.warning('Facebook did not return an access token')
        messages.error(request, 'Facebook لم يعيد رمز الوصول (access token)')
        return redirect('login')

    # Fetch user profile (id, name, email)
    try:
        profile_resp = http_requests.get(
            FACEBOOK_USERINFO_URL,
            params={
                'fields': 'id,name,email',
                'access_token': access_token,
            },
            timeout=10,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()
    except http_requests.exceptions.RequestException as exc:
        logger.error(f'Facebook profile fetch failed: {exc}', exc_info=True)
        messages.error(request, 'فشل جلب ملف Facebook. يرجى المحاولة مجدداً')
        return redirect('login')
    except ValueError as exc:
        logger.error(f'Invalid JSON in Facebook profile: {exc}')
        messages.error(request, 'استجابة غير صحيحة من Facebook')
        return redirect('login')

    # Check for errors in profile response
    if 'error' in profile:
        error_msg = profile.get('error', {}).get('message', 'Unknown error')
        logger.warning(f'Facebook profile error: {error_msg}')
        messages.error(request, f'خطأ من Facebook: {error_msg}')
        return redirect('login')

    facebook_id = profile.get('id')
    email = profile.get('email', '')
    name = profile.get('name', '')

    if not facebook_id:
        logger.warning(f'Facebook profile missing ID for email {email}')
        messages.error(request, 'معرّف Facebook غير متوفر')
        return redirect('login')

    try:
        user = _get_or_create_social_user(email, name, 'facebook', facebook_id)
    except ValueError as exc:
        logger.warning(f'Social user creation error: {exc}')
        messages.error(request, str(exc))
        return redirect('login')
    except Exception as exc:
        logger.error(f'Social user creation failed (Facebook): {exc}', exc_info=True)
        messages.error(request, 'فشل إعداد الحساب. يرجى التواصل مع الدعم')
        return redirect('login')

    # Log in the user
    try:
        auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info(f'User {user.email} logged in via Facebook')
        messages.success(request, f'مرحباً {user.name}! تم تسجيل الدخول بنجاح')
        return redirect('dashboard')
    except Exception as exc:
        logger.error(f'Login failed for user {user.email}: {exc}', exc_info=True)
        messages.error(request, 'فشل تسجيل الدخول. يرجى المحاولة مجدداً')
        return redirect('login')
