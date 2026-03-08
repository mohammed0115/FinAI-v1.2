# Quick Start Guide - Social Login
# دليل البدء السريع - تسجيل الدخول الاجتماعي

## ⚡ خطوات البدء السريعة (5 دقائق)

### 1️⃣ إعداد Google OAuth2

**الخطوة 1: إنشاء Project**
1. اذهب إلى: https://console.cloud.google.com/
2. Create Project
3. اختر اسماً مثل "FinAI Login"

**الخطوة 2: Credentials**
1. APIs & Services → Credentials → Create Credentials
2. اختر OAuth 2.0 Client ID → Web Application
3. في "Authorized redirect URIs"، أضف:
   ```
   http://localhost:8000/auth/google/callback/
   https://yourdomain.com/auth/google/callback/
   ```
   اضغط CREATE

**الخطوة 3: انسخ البيانات**
- Client ID: `...apps.googleusercontent.com`
- Client Secret: `...`

**الخطوة 4: تحديث .env**
```env
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 2️⃣ إعداد Facebook OAuth2

**الخطوة 1: إنشاء App**
1. اذهب إلى: https://developers.facebook.com/
2. My Apps → Create App
3. اختر Consumer
4. ملء البيانات وانظر SKIP لـ business verification

**الخطوة 2: Facebook Login**
1. Add Product → Facebook Login
2. اختر Web
3. في Settings → Valid OAuth Redirect URIs، أضف:
   ```
   http://localhost:8000/auth/facebook/callback/
   https://yourdomain.com/auth/facebook/callback/
   ```

**الخطوة 3: انسخ البيانات**
1. في Settings → Basic
   - App ID
   - App Secret

**الخطوة 4: تحديث .env**
```env
FACEBOOK_APP_ID=your-app-id
FACEBOOK_APP_SECRET=your-app-secret
```

### 3️⃣ تشغيل النظام

```bash
cd /home/mohamed/FinAI-v1.2/backend

# تفعيل البيئة
source venv/bin/activate

# تطبيق migrations
python manage.py migrate

# تشغيل السيرفر
python manage.py runserver

# ثم افتح:
# http://localhost:8000/login/
```

### 4️⃣ اختبار الدخول

1. افتح http://localhost:8000/login/
2. اضغط "Continue with Google"
3. سجّل الدخول بحساب Google
4. يجب أن تُعاد إلى Dashboard

---

## 🔍 Debugging

### المشكلة: "خدمة Google OAuth غير مكوّنة"
```python
# تحقق من .env
echo $GOOGLE_CLIENT_ID
# يجب أن يظهر Client ID
```

### المشكلة: "تحقق الأمان فشل"
```python
# الجلسة انتهت. جرب:
# 1. امسح cookies المتصفح
# 2. أعد محاولة تسجيل الدخول
```

### المشكلة: "استجابة غير صحيحة من Google"
```python
# تأكد من أن Redirect URI متطابقة تماماً
# يجب أن تكون متطابقة في جميع الأماكن:
# 1. في Google Console
# 2. في الكود
# 3. في البيانات المُرسلة
```

### المشكلة: Callback URL مختلفة
```python
# Google يتوقع:
http://localhost:8000/auth/google/callback/

# إذا كانت مختلفة:
http://localhost:8000/auth/google/callback
# (بدون slash في النهاية)

# ستحصل على error: redirect_uri_mismatch
```

---

## 📝 ملفات مهمة

```
backend/
├── core/
│   ├── models.py                 ← User model
│   ├── social_auth_views.py      ← OAuth logic
│   ├── web_urls.py               ← OAuth URLs
│   └── web_views.py              ← Other views
├── FinAI/
│   ├── settings.py               ← GOOGLE_CLIENT_ID من هنا
│   └── urls.py                   ← Main URLs
├── templates/
│   └── login.html                ← أزرار Google & Facebook
└── .env                          ← OAuth credentials
```

---

## 🚀 الاختبار

### اختبار تلقائي
```bash
# تشغيل جميع الاختبارات
python manage.py test core.tests.test_social_auth --verbosity=2

# اختبار معين
python manage.py test core.tests.test_social_auth.GoogleOAuthTestCase

# مع coverage
coverage run --source='core' manage.py test core.tests.test_social_auth
coverage report
```

### في المتصفح
```
1. افتح http://localhost:8000/login/
2. اضغط "Continue with Google"
3. سيتم نقلك إلى Google OAuth
4. قم بتسجيل الدخول
5. الموافقة على الصلاحيات
6. يجب أن تُعاد إلى Dashboard
```

---

## 🔐 Production Checklist

- [ ] GOOGLE_CLIENT_ID و GOOGLE_CLIENT_SECRET معدّة في Secrets Manager
- [ ] FACEBOOK_APP_ID و FACEBOOK_APP_SECRET معدّة في Secrets Manager
- [ ] HTTPS مفعّل
- [ ] Redirect URIs محدّثة على Google Console و Facebook Developers
- [ ] `SECURE_SSL_REDIRECT = True` في settings.py
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] Database migrated
- [ ] Tests نجحت

---

## 🔗 الروابط المفيدة

### Google Connect
- Google Cloud Console: https://console.cloud.google.com/
- OAuth Credentials: https://console.cloud.google.com/apis/credentials
- Google+ API: https://console.cloud.google.com/apis/library/plus.googleapis.com

### Facebook Connect
- Facebook Developers: https://developers.facebook.com/
- My Apps: https://developers.facebook.com/apps/
- Settings → Basic: حيث تجد App ID و App Secret

### Documentation
- Social Login Setup: [SOCIAL_LOGIN_SETUP.md](SOCIAL_LOGIN_SETUP.md)
- Project Structure: [backend/](backend/)
- Tests: [backend/core/tests/test_social_auth.py](backend/core/tests/test_social_auth.py)

---

## 💡 نصائح

1. **استخدم Localhost ID لـ Testing**
   - Google يقبل `http://localhost:8000/...`
   - Facebook يقبل `http://localhost:8000/...`
   - لا تحتاج HTTPS for localhost

2. **قم بتحديث credentials في .env فقط**
   - لا تضع secrets في الكود
   - استخدم .env للتطوير
   - استخدم Secrets Manager للإنتاج

3. **تفعيل Google+ API**
   - بدون تفعيل Google+ API، لن تتمكن من جلب بيانات المستخدم
   - في Google Cloud Console:
     - اذهب إلى APIs & Services → Library
     - ابحث عن "Google+ API"
     - اضغط Enable

4. **Facebook Public Profile**
   - بعض المستخدمين قد يختبئون بياناتهم
   - افطرض أن البريد قد لا يكون متاحاً دائماً
   - لديك معالجة خطأ لهذا الحالة

---

## 🆘 الدعم

**للمشاكل التقنية:**
1. تحقق من logs: `tail -f logs/django.log`
2. افتح المتصفح DevTools (F12)
3. تحقق من Network tab لرؤية الـ redirects
4. تحقق من .env:
   ```bash
   python manage.py shell
   from django.conf import settings
   print(settings.GOOGLE_CLIENT_ID)
   ```

---

**آخر تحديث:** March 8, 2026  
**الإصدار:** 1.0  
**الحالة:** ✅ Ready
