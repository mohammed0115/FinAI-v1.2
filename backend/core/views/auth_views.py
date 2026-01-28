"""
Authentication Views - وجهات المصادقة
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.db import transaction
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
    """صفحة تسجيل شركة جديدة"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        tax_number = request.POST.get('tax_number')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        company_logo = request.FILES.get('company_logo')
        
        # Validation
        if password != password_confirm:
            messages.error(request, 'كلمات المرور غير متطابقة')
            return render(request, 'login.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'البريد الإلكتروني مسجل مسبقاً')
            return render(request, 'login.html')
        
        if Organization.objects.filter(vat_number=tax_number).exists():
            messages.error(request, 'الرقم الضريبي مسجل مسبقاً')
            return render(request, 'login.html')
        
        try:
            with transaction.atomic():
                # Create Organization
                org = Organization.objects.create(
                    name=company_name,
                    name_ar=company_name,
                    vat_number=tax_number,
                    country='SA',
                )
                
                # Save logo if provided
                if company_logo:
                    org.logo = company_logo
                    org.save()
                
                # Create Admin User
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=full_name.split()[0] if full_name else '',
                    last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                    organization=org,
                    role='admin',
                )
                
                messages.success(request, 'تم إنشاء الحساب بنجاح! يمكنك الآن تسجيل الدخول')
                return redirect('login')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء إنشاء الحساب: {str(e)}')
    
    return render(request, 'login.html')


def logout_view(request):
    """تسجيل الخروج"""
    auth_logout(request)
    return redirect('login')

