from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect, render

from core.application.authentication import (
    RegisterUserCommand,
    login_user_use_case,
    register_user_use_case,
)
from core.views.base import OrganizationActionView


class LoginPageView(OrganizationActionView):
    template_name = 'login.html'
    require_authentication = False
    require_organization = False

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')

        result = login_user_use_case.execute(
            request=request,
            email=request.POST.get('email'),
            password=request.POST.get('password'),
        )
        if result.succeeded:
            auth_login(request, result.user)
            return redirect('dashboard')

        for error in result.errors:
            messages.error(request, error)
        return render(request, self.template_name)


class LandingPageView(OrganizationActionView):
    template_name = 'landing.html'
    require_authentication = False
    require_organization = False

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name)


class RegisterPageView(OrganizationActionView):
    template_name = 'login.html'
    require_authentication = False
    require_organization = False
    active_tab = 'register'

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')
        return render(request, self.template_name, {'active_tab': self.active_tab})

    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard')

        command = RegisterUserCommand(
            full_name=(request.POST.get('full_name') or request.POST.get('name') or '').strip(),
            email=(request.POST.get('email') or '').strip().lower(),
            password=request.POST.get('password') or '',
            password_confirm=request.POST.get('password_confirm') or request.POST.get('confirm_password') or '',
            organization_name=(request.POST.get('company_name') or '').strip(),
            tax_number=(request.POST.get('tax_number') or '').strip(),
            company_logo=request.FILES.get('company_logo'),
        )

        result = register_user_use_case.execute(command)
        if result.succeeded:
            auth_login(request, result.user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'تم إنشاء الحساب بنجاح')
            return redirect('dashboard')

        for error in result.errors:
            messages.error(request, error)
        return render(request, self.template_name, {'active_tab': self.active_tab})


class LogoutPageView(OrganizationActionView):
    require_authentication = False
    require_organization = False

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return redirect('login')

    post = get


login_view = LoginPageView.as_view()
landing_view = LandingPageView.as_view()
register_view = RegisterPageView.as_view()
logout_view = LogoutPageView.as_view()


__all__ = [
    'LoginPageView',
    'LandingPageView',
    'RegisterPageView',
    'LogoutPageView',
    'login_view',
    'landing_view',
    'register_view',
    'logout_view',
]
