# Social Login API - API Documentation
# وثائق API - تسجيل الدخول الاجتماعي

## 🔗 Available Endpoints

### Google OAuth2

#### 1. Initiate Google Login
```
GET /auth/google/
```

**Purpose:** Redirect user to Google's OAuth consent page

**Response:**
- 302 Redirect to Google OAuth URL
- Sets `oauth_state` in session

**Example:**
```bash
curl -L "http://localhost:8000/auth/google/"
# Redirects to:
# https://accounts.google.com/o/oauth2/v2/auth?
#   client_id=...
#   redirect_uri=http://localhost:8000/auth/google/callback/
#   response_type=code
#   scope=openid+email+profile
#   state=...
```

**Session Data Created:**
```python
{
    'oauth_state': 'random_token_123...'  # CSRF protection
}
```

---

#### 2. Google OAuth Callback
```
GET /auth/google/callback/
```

**Query Parameters:**
```
code: string      # Authorization code from Google
state: string     # CSRF token (must match session)
error: string     # (Optional) Error code if user cancelled
```

**Response:**
- 302 Redirect to `/dashboard/` on success
- 302 Redirect to `/login/` on error
- 400 Bad Request if CSRF check fails

**Flow:**
1. Exchange `code` for `access_token`
2. Fetch user profile from Google
3. Create or link user account
4. Log user in
5. Redirect to dashboard

**Example Success:**
```bash
# User clicks approve on Google
# Google redirects to:
curl "http://localhost:8000/auth/google/callback/?code=abc123xyz&state=xyz123abc"

# Response:
# 302 Redirect to /dashboard/
```

**Example Error (User Cancelled):**
```bash
curl "http://localhost:8000/auth/google/callback/?error=access_denied&state=xyz123abc"

# Response:
# 302 Redirect to /login/
# Message: "تم إلغاء تسجيل الدخول عبر Google"
```

---

### Facebook OAuth2

#### 1. Initiate Facebook Login
```
GET /auth/facebook/
```

**Purpose:** Redirect user to Facebook's OAuth consent page

**Response:**
- 302 Redirect to Facebook OAuth URL
- Sets `oauth_state` in session

**Example:**
```bash
curl -L "http://localhost:8000/auth/facebook/"
# Redirects to:
# https://www.facebook.com/v18.0/dialog/oauth?
#   client_id=...
#   redirect_uri=http://localhost:8000/auth/facebook/callback/
#   response_type=code
#   scope=email,public_profile
#   state=...
```

**Session Data Created:**
```python
{
    'oauth_state': 'random_token_456...'  # CSRF protection
}
```

---

#### 2. Facebook OAuth Callback
```
GET /auth/facebook/callback/
```

**Query Parameters:**
```
code: string              # Authorization code from Facebook
state: string             # CSRF token (must match session)
error_reason: string      # (Optional) Error code if user cancelled
error_description: string # (Optional) Error description
```

**Response:**
- 302 Redirect to `/dashboard/` on success
- 302 Redirect to `/login/` on error
- 400 Bad Request if CSRF check fails

**Flow:**
1. Exchange `code` for `access_token`
2. Fetch user profile from Facebook (id, name, email)
3. Create or link user account
4. Log user in
5. Redirect to dashboard

**Example Success:**
```bash
# User clicks approve on Facebook
# Facebook redirects to:
curl "http://localhost:8000/auth/facebook/callback/?code=def456uvw&state=uvw456def"

# Response:
# 302 Redirect to /dashboard/
```

**Example Error (User Cancelled):**
```bash
curl "http://localhost:8000/auth/facebook/callback/?error_reason=user_denied&state=uvw456def"

# Response:
# 302 Redirect to /login/
# Message: "تم إلغاء تسجيل الدخول عبر Facebook"
```

---

## 📊 Internal API

### User Creation/Linking Function

```python
# في core/social_auth_views.py

_get_or_create_social_user(
    email: str,           # User's email
    name: str,            # User's name
    provider: str,        # 'google' or 'facebook'
    provider_id: str      # Unique ID from provider
) -> User
```

**Returns:**
```python
User(
    id: UUID,
    email: str,
    name: str,
    google_id: str or None,
    facebook_id: str or None,
    social_provider: str,  # 'google', 'facebook', or 'email'
    is_active: bool,
    created_at: datetime,
    last_signed_in: datetime,
)
```

**Raises:**
- `ValueError`: If email or provider_id missing

**Usage:**
```python
from core.social_auth_views import _get_or_create_social_user

user = _get_or_create_social_user(
    email='user@gmail.com',
    name='John Doe',
    provider='google',
    provider_id='12345'
)
```

**Logic:**
```
1. Check if user exists by provider_id → Return user
2. Check if user exists by email → Link provider_id → Return user
3. Create new user with provider_id → Return user
```

---

## 🔐 Security Features

### 1. CSRF Protection
Every OAuth request includes:
- Random `state` token generated per request
- Token stored in session
- Token verified on callback
- Token expires after 10 minutes

```python
# Request:
state = secrets.token_urlsafe(32)
request.session['oauth_state'] = state

# Callback:
if request.GET['state'] != request.session.pop('oauth_state', None):
    return HttpResponseBadRequest('Invalid OAuth state')
```

### 2. Session Security
- Session expires in 10 minutes for OAuth state
- Session timeout per Django settings
- Secure session cookies in production (HTTPS)

### 3. Data Validation
- Email is required to create account
- Provider ID is required
- Invalid responses are rejected with clear errors

### 4. Error Handling
All errors are caught and logged:
- Network errors
- Invalid responses
- Missing credentials
- CSRF failures

---

## 📋 Request/Response Examples

### Complete Google OAuth Flow

**Step 1: User clicks "Continue with Google"**
```
GET /auth/google/
```

**Response:**
```
302 Redirect to https://accounts.google.com/o/oauth2/v2/auth?...
Set-Cookie: sessionid=abc123; HttpOnly; SameSite=Lax
```

**Session now contains:**
```python
{
    'oauth_state': 'GvN_SxgEICAA...' ,  # Random token
    'sessionid': 'abc123'
}
```

---

**Step 2: User logs in and approves on Google**
```
Google redirects to:
GET /auth/google/callback/?code=4/0AWtgzBrR5...&state=GvN_SxgEICAA...
```

---

**Step 3: Backend processes callback**

**Internal flow:**
```
1. GET /auth/google/callback/?code=...&state=...
2. Validate state matches session
3. Exchange code for access_token:
   POST https://oauth2.googleapis.com/token
   {
       "code": "4/0AWtgzBrR5...",
       "client_id": "123.apps.googleusercontent.com",
       "client_secret": "secret",
       "redirect_uri": "http://localhost:8000/auth/google/callback/",
       "grant_type": "authorization_code"
   }

4. Google returns:
   {
       "access_token": "ya29.a0AWY...",
       "expires_in": 3599,
       "token_type": "Bearer"
   }

5. Fetch user profile:
   GET https://www.googleapis.com/oauth2/v2/userinfo
   Authorization: Bearer ya29.a0AWY...

6. Google returns:
   {
       "id": "123456789",
       "email": "user@gmail.com",
       "name": "John Doe",
       ...
   }

7. Create or link user:
   User.objects.create_user(
       email='user@gmail.com',
       name='John Doe',
       google_id='123456789',
       social_provider='google',
       is_active=True
   )

8. Log user in:
   auth_login(request, user)

9. Redirect to dashboard
```

**Response:**
```
302 Redirect to /dashboard/
Set-Cookie: sessionid=xyz789; HttpOnly; SameSite=Lax
```

---

### Complete Facebook OAuth Flow

**Similar to Google, but:**
1. Redirect to: `https://www.facebook.com/v18.0/dialog/oauth`
2. Token endpoint: `https://graph.facebook.com/v18.0/oauth/access_token`
3. Profile endpoint: `https://graph.facebook.com/me?fields=id,name,email`
4. Uses `access_token` directly in query params for profile fetch

---

## 🔧 Configuration

### Required Environment Variables

```env
# Google
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>

# Facebook
FACEBOOK_APP_ID=<your-app-id>
FACEBOOK_APP_SECRET=<your-app-secret>
```

### Django Settings

```python
# settings.py

# User model
AUTH_USER_MODEL = 'core.User'

# Authentication backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = True  # Production only
SESSION_COOKIE_SAMESITE = 'Lax'

# OAuth URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
```

---

## 📚 URL Patterns

All URLs are in `core/web_urls.py`:

```python
path('auth/google/', google_login, name='google_login'),
path('auth/google/callback/', google_callback, name='google_callback'),
path('auth/facebook/', facebook_login, name='facebook_login'),
path('auth/facebook/callback/', facebook_callback, name='facebook_callback'),
```

---

## 🧪 Testing

### Test the Endpoints

```bash
# Start OAuth flow
curl -i http://localhost:8000/auth/google/
# Returns 302 redirect

# Test with invalid state (simulates CSRF attack)
curl -i "http://localhost:8000/auth/google/callback/?code=test&state=invalid"
# Returns 302 to /login/
```

### Run Unit Tests

```bash
# All tests
python manage.py test core.tests.test_social_auth

# Google tests only
python manage.py test core.tests.test_social_auth.GoogleOAuthTestCase

# Facebook tests only
python manage.py test core.tests.test_social_auth.FacebookOAuthTestCase

# With verbose output
python manage.py test core.tests.test_social_auth --verbosity=2

# With coverage
coverage run --source='core' manage.py test core.tests.test_social_auth
coverage report
```

---

## 📝 Logging

All OAuth operations are logged:

```python
# In logs/django.log

[INFO] Redirecting to Google OAuth: http://localhost:8000/auth/google/callback/
[INFO] Found existing user test@gmail.com by google_id
[INFO] Linking facebook account to existing user test@gmail.com
[INFO] Creating new user account from facebook login: newuser@fb.com
[INFO] User test@gmail.com logged in via Google
[WARNING] CSRF state validation failed for Google OAuth
[WARNING] Google login attempted but GOOGLE_CLIENT_ID not configured
[ERROR] Google token exchange failed: Connection timeout
[ERROR] Google profile fetch failed: 403 Forbidden
```

---

## ✅ Expected Behaviors

### New User (Google)
```
User email: newuser@gmail.com
1. Does not exist in database
2. Google returns email, name, and id
3. New account created
4. google_id stored
5. User logged in automatically
6. Redirected to /dashboard/
```

### Existing User (Google)
```
User email: existing@email.com
1. Already exists in database (created via email/password)
2. google_id linked
3. social_provider updated
4. User logged in
5. Redirected to /dashboard/
```

### User Cancels Login
```
1. User clicks "Cancel" on OAuth provider
2. Provider redirects with error=access_denied
3. Caught and logged
4. User redirected to /login/ with error message
5. No account created or modified
```

### CSRF Attack Prevented
```
1. Attacker tries to use old/different state token
2. State validation fails
3. Request rejected
4. User redirected to /login/
5. Attack prevented
```

---

**API Version:** 1.0  
**Last Updated:** March 8, 2026  
**Status:** ✅ Production Ready
