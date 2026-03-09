"""
Authentication Views - وجهات المصادقة
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from core.models import User, Organization


def login_view(request):
    """صفحة تسجيل الدخول"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'بيانات الدخول غير صحيحة')
    
    return render(request, 'login.html')


def register_view(request):
    """Register view"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        company_name = (request.POST.get('company_name') or '').strip()
        tax_number = (request.POST.get('tax_number') or '').strip()
        full_name = (request.POST.get('full_name') or '').strip()
        email = (request.POST.get('email') or '').strip().lower()
        password = request.POST.get('password') or ''
        password_confirm = request.POST.get('password_confirm') or ''
        company_logo = request.FILES.get('company_logo')

        # Validation
        if not full_name:
            messages.error(request, 'يرجى إدخال الاسم')
            return render(request, 'login.html', {'active_tab': 'register'})

        if not email:
            messages.error(request, 'يرجى إدخال البريد الإلكتروني')
            return render(request, 'login.html', {'active_tab': 'register'})

        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'يرجى إدخال بريد إلكتروني صحيح')
            return render(request, 'login.html', {'active_tab': 'register'})

        if password != password_confirm:
            messages.error(request, 'كلمتا المرور غير متطابقتين')
            return render(request, 'login.html', {'active_tab': 'register'})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'البريد الإلكتروني مسجل مسبقاً')
            return render(request, 'login.html', {'active_tab': 'register'})

        if tax_number and Organization.objects.filter(vat_number=tax_number).exists():
            messages.error(request, 'الرقم الضريبي مسجل مسبقاً')
            return render(request, 'login.html', {'active_tab': 'register'})

        try:
            with transaction.atomic():
                org = None
                if company_name:
                    # Create Organization only if provided (optional for later onboarding)
                    org = Organization.objects.create(
                        name=company_name,
                        name_ar=company_name,
                        vat_number=tax_number or None,
                        country='SA',
                    )

                # Save logo if provided
                if org and company_logo:
                    org.logo = company_logo
                    org.save()

                # Create Admin User
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    name=full_name,
                    organization=org,
                    role='admin',
                    social_provider='email',
                    login_method='email',
                )

                messages.success(request, 'تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول')
                return redirect('login')

        except Exception as e:
            messages.error(request, f"حدث خطأ أثناء إنشاء الحساب: {str(e)}")
            return render(request, 'login.html', {'active_tab': 'register'})

    return render(request, 'login.html', {'active_tab': 'register'})


def logout_view(request):
    """تسجيل الخروج"""
    auth_logout(request)
    return redirect('login')

