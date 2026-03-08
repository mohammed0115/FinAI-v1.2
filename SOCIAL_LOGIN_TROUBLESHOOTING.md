# Social Login - Troubleshooting Guide
# دليل حل المشاكل - تسجيل الدخول الاجتماعي

## 🔴 المشاكل الشائعة وحلولها

---

## ❌ المشكلة 1: "خدمة Google OAuth غير مكوّنة"

### الأعراض
- عند الضغط على "Continue with Google"
- رسالة: "خدمة Google OAuth غير مكوّنة. يرجى التواصل مع الدعم"

### الأسباب المحتملة
1. `GOOGLE_CLIENT_ID` لم يتم تعيينها في `.env`
2. قيمة فارغة أو خاطئة

### الحل

**الخطوة 1: تحقق من .env**
```bash
cd /home/mohamed/FinAI-v1.2/backend
cat .env | grep GOOGLE_CLIENT_ID
```

يجب أن تراها:
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

**الخطوة 2: إذا كانت فارغة**
1. اذهب إلى Google Cloud Console: https://console.cloud.google.com/
2. APIs & Services → Credentials
3. انسخ الـ Client ID
4. في `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-actual-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-actual-secret
   ```

**الخطوة 3: أعد تشغيل السيرفر**
```bash
python manage.py runserver
```

**الخطوة 4: اختبر في shell**
```bash
python manage.py shell
from django.conf import settings
print(f"Client ID: {settings.GOOGLE_CLIENT_ID}")
print(f"Has value: {bool(settings.GOOGLE_CLIENT_ID)}")
```

---

## ❌ المشكلة 2: "تحقق الأمان فشل" (CSRF Error)

### الأعراض
- عند الرجوع من Google OAuth
- رسالة: "تحقق الأمان فشل. يرجى المحاولة مجدداً"

### الأسباب المحتملة
1. **Expired Session** - انتهت جلسة المتصفح
2. **Cookie Cleared** - تم حذف cookies المتصفح
3. **Timeout** - استغرقت عملية OAuth أكثر من 10 دقائق
4. **Browser Tabs** - فتح OAuth في tab منفصل وفقدت الـ session

### الحل

**الحل السريع:**
```bash
# امسح cookies المتصفح وأعد محاولة
1. افتح http://localhost:8000/login/
2. Ctrl+Shift+Delete (أو اذهب إلى Settings → Privacy)
3. امسح الـ Cookies
4. أعد تحميل الصفحة
5. جرّب تسجيل الدخول مرة أخرى
```

**الحل التقني:**
تحقق من أن الـ session timeout طويل بما يكفي في `settings.py`:
```python
# في FinAI/settings.py
SESSION_COOKIE_AGE = 1209600  # أسبوعين
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

---

## ❌ المشكلة 3: "error: redirect_uri_mismatch"

### الأعراض
- عند الضغط على "Continue with Google"
- Google يشتكي: `redirect_uri_mismatch`

### السبب
الـ Redirect URI في Google Console لا تطابق الـ URI في الكود

### الحل

**الخطوة 1: تحقق من الـ Redirect URI في الكود**
```bash
# من المشروع
grep -r "auth/google/callback" backend/

# يجب أن ترى:
# /auth/google/callback/
```

**الخطوة 2: تحقق من الـ Redirect URI في Google Console**
1. اذهب إلى: https://console.cloud.google.com/apis/credentials
2. اختر OAuth 2.0 Client ID
3. انظر إلى "Authorized redirect URIs"
4. يجب أن تكون موجودة:
   ```
   http://localhost:8000/auth/google/callback/
   https://yourdomain.com/auth/google/callback/
   ```

**الخطوة 3: تأكد من تطابق الـ Slash**
- ❌ الخطأ الشائع: `callback` (بدون slash)
- ✅ الصحيح: `callback/` (مع slash)

**الخطوة 4: إذا كانت مختلفة**
1. في Google Console، احذف الـ Redirect URI القديمة
2. أضف الـ Redirect URI الصحيحة:
   ```
   http://localhost:8000/auth/google/callback/
   ```
3. اضغط Save
4. أعد تحميل المتصفح

**الخطوة 5: اختبر مرة أخرى**

---

## ❌ المشكلة 4: "استجابة غير صحيحة من Google"

### الأعراض
- عند محاولة تسجيل الدخول
- رسالة: "استجابة غير صحيحة من Google"

### الأسباب المحتملة
1. Google+ API غير مفعّلة
2. خطأ في البيانات المُرسلة
3. مشكلة في الاتصال بالإنترنت

### الحل

**الخطوة 1: تفعيل Google+ API**
1. اذهب إلى Google Cloud Console
2. APIs & Services → Library
3. ابحث عن "Google+ API"
4. اضغط Enable (إذا لم تكن مفعّلة)

**الخطوة 2: تحقق من الأخطاء في Logs**
```bash
tail -f logs/django.log | grep -i google
```

يجب أن ترى شيئاً مثل:
```
[ERROR] Google profile fetch failed: 403 Forbidden
```

**الخطوة 3: إذا كان 403 Forbidden**
- Google+ API غير مفعّلة
- الحل: تفعيل Google+ API (خطوة 1)

---

## ❌ المشكلة 5: "لا توجد بيانات مستخدم من Google"

### الأعراض
- تسجيل الدخول نجح لكن لا توجد معلومات المستخدم
- حساب تم إنشاؤه بدون name أو email

### السبب
الـ scope غير كافي في Google OAuth request

### الحل

تحقق من الـ scope في `social_auth_views.py`:
```python
GOOGLE_SCOPES = 'openid email profile'
```

إذا كانت فقط `openid`:
```python
# ❌ خطأ
GOOGLE_SCOPES = 'openid'

# ✅ صحيح
GOOGLE_SCOPES = 'openid email profile'
```

أضف `email` و `profile` وأعد تشغيل السيرفر.

---

## ❌ المشكلة 6: Facebook: "خطأ من Facebook"

### الأعراض
- عند محاولة تسجيل الدخول عبر Facebook
- رسالة: "خطأ من Facebook"

### الحل

**الخطوة 1: تحقق من App ID و App Secret**
```bash
cat .env | grep FACEBOOK
```

**الخطوة 2: تحقق من Redirect URI**
1. اذهب إلى Facebook Developers
2. الذهاب إلى تطبيقك
3. Facebook Login → Settings
4. تحقق من "Valid OAuth Redirect URIs"
5. يجب أن تكون موجودة:
   ```
   http://localhost:8000/auth/facebook/callback/
   https://yourdomain.com/auth/facebook/callback/
   ```

**الخطوة 3: اختبر الاتصال**
```bash
curl "https://www.facebook.com/v18.0/dialog/oauth?client_id=YOUR_APP_ID"
```

---

## ❌ المشكلة 7: "المستخدم لم يتم لديه بريد إلكتروني"

### الأعراض
- عند تسجيل الدخول عبر Facebook
- رسالة: "لا يمكن إنشاء حساب بدون بريد إلكتروني"

### السبب
المستخدم لم يشارك بريده الإلكتروني مع Facebook

### الحل

**للمستخدم:**
1. اذهب إلى Facebook Settings
2. Privacy → من رأى بيانات الاتصال الخاصة بك
3. اجعل البريد الإلكتروني public
4. أعد محاولة تسجيل الدخول إلى FinAI

**للمطور:**
إذا أردت قبول مستخدمين بدون بريد:
```python
# في social_auth_views.py
# ملاحظة: لا ننصح بهذا
if not email:
    email = f"fb_{provider_id}@finai.local"
```

---

## ❌ المشكلة 8: "Session Expired"

### الأعراض
- عند العودة من OAuth
- رسالة: "الجلسة انتهت"

### السبب
وقت انتظار طويل جداً بين البدء والانتهاء من OAuth

### الحل

**الحل 1: جرّب مرة أخرى**
- ابدأ عملية OAuth الجديدة
- لا تأخذ أكثر من دقيقة

**الحل 2: تحقق من Session Settings**
```python
# في settings.py
SESSION_COOKIE_AGE = 1209600  # ساعات كافية
SESSION_SAVE_EVERY_REQUEST = True
```

---

## ❌ المشكلة 9: "Cross-Site Request"

### الأعراض
- خطأ "cross-site request" من المتصفح
- الـ cookies لا تُرسل في الـ callback

### السبب
SameSite cookie setting غير صحيح

### الحل

```python
# في settings.py
CSRF_COOKIE_SAMESITE = 'Lax'  # أو 'None' مع HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'

# في الإنتاج مع HTTPS:
CSRF_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
```

---

## 🔍 كيفية Debug

### 1. تحقق من الـ Logs

```bash
# مشاهدة جميع أخطاء Social Auth
tail -f logs/django.log | grep -i "google\|facebook\|oauth"

# مثال على الـ Output:
[INFO] Redirecting to Google OAuth: http://localhost:8000/auth/google/callback/
[INFO] Found existing user test@gmail.com by google_id
[WARNING] CSRF state validation failed for Google OAuth
[ERROR] Google token exchange failed: Connection timeout
```

### 2. استخدم Django Shell

```bash
python manage.py shell

# تحقق من الـ Settings
from django.conf import settings
print(settings.GOOGLE_CLIENT_ID)
print(settings.FACEBOOK_APP_ID)

# تحقق من المستخدمين
from core.models import User
User.objects.filter(social_provider='google').count()
```

### 3. استخدم Browser DevTools

```
1. افتح المتصفح → F12
2. انظر إلى Network tab
3. ابدأ عملية OAuth
4. ستشاهد redirects:
   - GET /auth/google/
   - GET https://accounts.google.com/o/oauth2/v2/auth?...
   - GET /auth/google/callback/?code=...&state=...
```

### 4. تفعيل Debug Mode

```python
# في settings.py
DEBUG = True  # ✅ في التطوير فقط
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'DEBUG'},
}
```

---

## 🛠️ أوامر مفيدة

```bash
# تشغيل السيرفر مع Debug
python manage.py runserver --settings=FinAI.settings

# تشغيل الاختبارات
python manage.py test core.tests.test_social_auth --verbosity=2

# عرض الـ Logs الحية
tail -f logs/django.log

# تفريغ قاعدة البيانات (Developer only!)
python manage.py reset_db --no-input

# إنشاء super user
python manage.py createsuperuser

# تطبيق Migrations
python manage.py migrate
```

---

## 📞 أين تطلب الدعم

### Google OAuth Issues
- Google Cloud Console: https://console.cloud.google.com/
- Docs: https://developers.google.com/identity/protocols/oauth2

### Facebook OAuth Issues
- Facebook Developers: https://developers.facebook.com/
- Docs: https://developers.facebook.com/docs/facebook-login/web

### Project Logs
```bash
# ابحث عن أخطاء في الـ Logs
grep ERROR logs/django.log
grep WARNING logs/django.log
```

---

## ✅ Checklist: هل تم كل شيء؟

- [ ] `GOOGLE_CLIENT_ID` معدّة في `.env`
- [ ] `GOOGLE_CLIENT_SECRET` معدّة في `.env`
- [ ] Google+ API مفعّلة في Google Cloud Console
- [ ] Redirect URI في Google Console تطابق `http://localhost:8000/auth/google/callback/`
- [ ] `FACEBOOK_APP_ID` معدّة في `.env`
- [ ] `FACEBOOK_APP_SECRET` معدّة في `.env`
- [ ] Valid OAuth Redirect URIs محدّثة في Facebook
- [ ] السيرفر تم إعادة تشغيله بعد تعديل `.env`
- [ ] Cookies المتصفح تم حذفها
- [ ] اختبار العمل بنجاح

---

**آخر تحديث:** March 8, 2026  
**الإصدار:** 1.0  
**الحالة:** ✅ Ready
