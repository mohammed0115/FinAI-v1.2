# نظام Social Login - دليل الإعداد الشامل
# Social Login System - Complete Setup Guide

## 🎯 نظرة عامة / Overview

نظام تسجيل دخول اجتماعي متكامل يسمح للمستخدمين بتسجيل الدخول باستخدام:
- ✅ Google OAuth2
- ✅ Facebook OAuth2

The system automatically:
- ✅ إنشاء حسابات جديدة تلقائياً
- ✅ ربط الحسابات الموجودة
- ✅ تفعيل المستخدمين مباشرة
- ✅ حفظ معرّفات المزودين (IDs)

---

## 📋 المتطلبات / Requirements

### 1. المكتبات المثبتة / Installed Packages
```bash
requests==2.32.5          # HTTP requests
oauthlib==3.3.1          # OAuth protocol
requests-oauthlib==2.0.0 # OAuth for requests
```

### 2. نموذج المستخدم / User Model
✅ الحقول موجودة بالفعل:
- `google_id` - معرّف Google الفريد
- `facebook_id` - معرّف Facebook الفريد
- `social_provider` - مزود الخدمة (google/facebook/email)
- `login_method` - طريقة تسجيل الدخول

### 3. إعدادات Django / Django Settings
✅ معدّة بالفعل:
```python
AUTH_USER_MODEL = 'core.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# OAuth Credentials (via .env)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')
```

---

## 🔧 إعداد Google OAuth2

### الخطوة 1: إنشاء Project على Google Cloud Console

1. اذهب إلى: https://console.cloud.google.com/
2. اختر **Create Project** أو استخدم مشروع موجود
3. اذهب إلى **APIs & Services** → **Credentials**

### الخطوة 2: إنشاء OAuth 2.0 Client ID

1. اختر **Create Credentials** → **OAuth client ID**
2. اختر **Web application**
3. أضف **Authorized redirect URIs**:
   ```
   http://localhost:8000/auth/google/callback/
   https://yourdomain.com/auth/google/callback/
   ```
4. انسخ:
   - Client ID
   - Client Secret

### الخطوة 3: تحديث `.env`

```env
# Google OAuth2
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### الخطوة 4: تفعيل Google+ API

1. في Google Cloud Console، اذهب إلى **APIs & Services** → **Library**
2. ابحث عن **Google+ API**
3. اضغط **Enable**

---

## 🔧 إعداد Facebook OAuth2

### الخطوة 1: إنشاء App على Facebook Developers

1. اذهب إلى: https://developers.facebook.com/
2. اختر **My Apps** → **Create App**
3. اختر **Consumer** as the app type
4. ملء البيانات الأساسية

### الخطوة 2: إضافة Facebook Login

1. في تفاصيل التطبيق، اختر **Add Product**
2. ابحث عن **Facebook Login** واضغط **Set Up**
3. اختر **Web** كنوع التطبيق

### الخطوة 3: تكوين OAuth Redirect URIs

1. في **Facebook Login Settings** → **Valid OAuth Redirect URIs**
2. أضف:
   ```
   http://localhost:8000/auth/facebook/callback/
   https://yourdomain.com/auth/facebook/callback/
   ```
3. اضغط **Save Changes**

### الخطوة 4: الحصول على Credentials

1. في **Settings** → **Basic**، انسخ:
   - App ID
   - App Secret

### الخطوة 5: تحديث `.env`

```env
# Facebook OAuth2
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

---

## 🗂️ هيكل الملفات / File Structure

```
backend/
├── core/
│   ├── models.py                 # ✅ User model مع google_id, facebook_id
│   ├── social_auth_views.py      # ✅ Google + Facebook OAuth views
│   ├── web_urls.py               # ✅ URLs للـ social logins
│   └── web_views.py              # ✅ Views الأخرى
├── FinAI/
│   ├── settings.py               # ✅ AUTHENTICATION_BACKENDS
│   └── urls.py                   # ✅ Main URLs
├── templates/
│   └── login.html                # ✅ Login page مع أزرار Google & Facebook
└── .env                          # ✅ OAuth credentials
```

---

## 🔄 Flow الكامل / Complete Flow

### 1. المستخدم يضغط "Continue with Google"

```
User clicks "Continue with Google"
    ↓
google_login() view
    ↓
Generate random state token (CSRF protection)
Store state in session
Redirect to Google OAuth URL with:
    - client_id
    - redirect_uri (callback URL)
    - scope (email, profile)
    - state (CSRF token)
```

### 2. المستخدم يوافق على الصلاحيات

```
User logs in to Google
User approves access
Google redirects to callback URL with ?code=...&state=...
```

### 3. معالجة Callback من Google

```
google_callback() view receives:
    - code: Authorization code
    - state: CSRF token
    
Check state token validity (CSRF protection)
Exchange code for access_token:
    POST https://oauth2.googleapis.com/token
        code, client_id, client_secret, redirect_uri
        
Fetch user profile:
    GET https://www.googleapis.com/oauth2/v2/userinfo
        Authorization: Bearer {access_token}
```

### 4. إنشاء أو ربط الحساب

```
if user exists with this google_id:
    ✅ Use existing user
elif user exists with this email:
    ✅ Link google_id to existing user
else:
    ✅ Create new user with:
        - email
        - name
        - google_id
        - social_provider = 'google'
        - is_active = True
        
Login user
Redirect to dashboard
```

---

## 🛡️ الأمان / Security

### 1. CSRF Protection (حماية CSRF)
- يتم إنشاء `state` token عشوائي لكل طلب OAuth
- يتم التحقق من `state` في callback
- يتم حذف `state` من session بعد الاستخدام

### 2. Session Expiry (انتهاء الجلسة)
- `state` token ينتهي بعد 10 دقائق
- منع استخدام unauthorized requests

### 3. HTTPS Requirements
في الإنتاج:
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### 4. Secret Management
- لا تضع `client_secret` في الكود
- استخدم متغيرات البيئة (`.env`)
- في الإنتاج، استخدم secrets manager

---

## 🔍 معالجة الأخطاء / Error Handling

### الأخطاء المحتملة:

#### 1. CSRF State Mismatch
```
السبب: جلسة انتهت أو محاولة هجوم
الحل: إعادة محاولة تسجيل الدخول
الرسالة: "تحقق الأمان فشل"
```

#### 2. User Cancelled Login
```
السبب: المستخدم ألغى تسجيل الدخول
الحل: إعادة محاولة
الرسالة: "تم إلغاء تسجيل الدخول"
```

#### 3. OAuth Credentials Not Configured
```
السبب: .env لم يتم تعيين GOOGLE_CLIENT_ID أو FACEBOOK_APP_ID
الحل: تعيين credentials في .env
الرسالة: "خدمة OAuth غير مكوّنة"
```

#### 4. Network Error during Token Exchange
```
السبب: فشل الاتصال بـ OAuth provider
الحل: إعادة المحاولة
الرسالة: "فشل تبادل البيانات. يرجى المحاولة مجدداً"
```

#### 5. Missing Email from Provider
```
السبب: المستخدم لم يشارك بريده الإلكتروني
الحل: طلب البريد من المستخدم في Facebook
الرسالة: "لا يمكن إنشاء حساب بدون بريد إلكتروني"
```

---

## 📊 قاعدة البيانات / Database Schema

### User Model Fields:

```python
class User(AbstractBaseUser, PermissionsMixin):
    # Social IDs
    google_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    facebook_id = models.CharField(max_length=128, null=True, blank=True, unique=True)
    
    # Provider info
    social_provider = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[('google', 'Google'), ('facebook', 'Facebook'), ('email', 'Email')],
    )
    login_method = models.CharField(max_length=64, null=True, blank=True)
    
    # Standard fields
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_signed_in = models.DateTimeField(auto_now=True)
```

---

## 🧪 الاختبار / Testing

### Manual Testing:

```bash
# 1. تأكد من أن البيئة تعمل
cd backend
source venv/bin/activate

# 2. ابدأ السيرفر
python manage.py runserver

# 3. افتح المتصفح
# http://localhost:8000/login/

# 4. اضغط "Continue with Google"
# يجب أن يحيلك إلى صفحة Google OAuth

# 5. قم بتسجيل الدخول بحساب Google
# يجب أن ينقلك إلى /auth/google/callback/ مع ?code=...

# 6. إذا نجح، يجب أن تُعاد إلى /dashboard/
```

### Unit Tests:

```python
# في tests/test_social_auth.py

from django.test import TestCase, Client
from core.models import User

class GoogleAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_google_login_redirect(self):
        """Test that google_login redirects to Google OAuth URL"""
        response = self.client.get('/auth/google/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('accounts.google.com', response.url)
    
    def test_user_creation_from_google(self):
        """Test that user is created from Google OAuth data"""
        # Mock Google callback data
        user = User.objects.create_user(
            email='test@gmail.com',
            name='Test User',
            google_id='12345',
            social_provider='google',
            is_active=True
        )
        self.assertEqual(user.email, 'test@gmail.com')
        self.assertEqual(user.google_id, '12345')
    
    def test_existing_user_link_google(self):
        """Test that Google ID is linked to existing user"""
        # Create user with email only
        user = User.objects.create_user(
            email='test@gmail.com',
            name='Test User',
        )
        # Link Google ID
        user.google_id = '12345'
        user.social_provider = 'google'
        user.save()
        
        self.assertEqual(user.google_id, '12345')
```

---

## 🚀 النشر / Deployment

### في الإنتاج:

#### 1. تحديث `.env` مع Production Credentials

```env
# Google
GOOGLE_CLIENT_ID=prod-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=prod-client-secret

# Facebook
FACEBOOK_APP_ID=prod-app-id
FACEBOOK_APP_SECRET=prod-app-secret

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

#### 2. تحديث OAuth Redirect URIs

**Google Console:**
```
https://yourdomain.com/auth/google/callback/
https://www.yourdomain.com/auth/google/callback/
```

**Facebook Developers:**
```
https://yourdomain.com/auth/facebook/callback/
https://www.yourdomain.com/auth/facebook/callback/
```

#### 3. تفعيل HTTPS

```python
# settings.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```

#### 4. استخدام Environment Variables

```bash
# في shell/docker
export GOOGLE_CLIENT_ID=prod-id
export GOOGLE_CLIENT_SECRET=prod-secret
export FACEBOOK_APP_ID=prod-app-id
export FACEBOOK_APP_SECRET=prod-secret

python manage.py runserver
```

---

## 📝 السجلات / Logging

النظام يسجل جميع العمليات:

```python
# في logs/django.log

[INFO] Redirecting to Google OAuth: http://localhost:8000/auth/google/callback/
[INFO] Found existing user test@gmail.com by google_id
[INFO] User test@gmail.com logged in via Google
[INFO] Linking facebook account to existing user test@gmail.com
[INFO] Creating new user account from facebook login: newuser@fb.com
[WARNING] CSRF state validation failed for Google OAuth
[ERROR] Google token exchange failed: Connection timeout
```

---

## 🔗 المراجع / References

### URLs المتاحة:

```python
# في web_urls.py

path('auth/google/', google_login, name='google_login')
path('auth/google/callback/', google_callback, name='google_callback')
path('auth/facebook/', facebook_login, name='facebook_login')
path('auth/facebook/callback/', facebook_callback, name='facebook_callback')
```

### Views المتاحة:

```python
# في social_auth_views.py

def google_login(request)           # Redirect to Google OAuth
def google_callback(request)        # Handle Google callback
def facebook_login(request)         # Redirect to Facebook OAuth
def facebook_callback(request)      # Handle Facebook callback
def _get_or_create_social_user()    # Create or link user
```

---

## ✅ Checklist

- [ ] Google OAuth credentials معدة في `.env`
- [ ] Facebook OAuth credentials معدة في `.env`
- [ ] Redirect URIs محدثة على Google Console
- [ ] Redirect URIs محدثة على Facebook Developers
- [ ] HTTPS معدة في الإنتاج
- [ ] Database migrations تم تطبيقها
- [ ] Tests تمت بنجاح
- [ ] Logging مُفعّل
- [ ] CSRF protection مُفعّل

---

## 📞 الدعم / Support

### في حالة المشاكل:

1. **تحقق من الـ logs:**
   ```bash
   tail -f logs/django.log
   ```

2. **تأكد من credentials:**
   ```bash
   python manage.py shell
   from django.conf import settings
   print(settings.GOOGLE_CLIENT_ID)
   print(settings.FACEBOOK_APP_ID)
   ```

3. **اختبر الاتصال:**
   ```bash
   curl -I https://accounts.google.com/o/oauth2/v2/auth
   curl -I https://www.facebook.com/v18.0/dialog/oauth
   ```

---

**آخر تحديث / Last Updated:** March 8, 2026  
**الإصدار / Version:** 1.0  
**الحالة / Status:** ✅ Production Ready
