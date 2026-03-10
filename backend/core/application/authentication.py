from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from core.models import Organization, User


@dataclass
class AuthenticationResult:
    user: Optional[User] = None
    errors: List[str] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.user is not None and not self.errors


@dataclass(frozen=True)
class RegisterUserCommand:
    full_name: str
    email: str
    password: str
    password_confirm: str
    organization_name: str = ''
    tax_number: str = ''
    company_logo: Any = None


class LoginUserUseCase:
    """Authenticate a user and ensure tenant setup is ready before sign-in."""

    def execute(self, *, request, email: str, password: str) -> AuthenticationResult:
        user = authenticate(request, email=(email or '').strip(), password=password or '')
        if user is None:
            return AuthenticationResult(errors=['بيانات الدخول غير صحيحة'])

        User.objects.ensure_organization_setup(user)
        return AuthenticationResult(user=user)


class RegisterUserUseCase:
    """Validate registration input and provision the initial tenant setup."""

    def execute(self, command: RegisterUserCommand) -> AuthenticationResult:
        errors = self._validate(command)
        if errors:
            return AuthenticationResult(errors=errors)

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=command.email,
                    password=command.password,
                    name=command.full_name,
                    role='admin',
                    social_provider='email',
                    login_method='email',
                    organization_name=command.organization_name,
                    organization_member_role='owner',
                )

                if user.organization:
                    if command.organization_name:
                        user.organization.name = command.organization_name
                        user.organization.name_ar = command.organization_name
                    if command.tax_number:
                        user.organization.vat_number = command.tax_number
                    if command.company_logo:
                        user.organization.logo = command.company_logo
                    user.organization.save()

                return AuthenticationResult(user=user)
        except Exception as exc:
            return AuthenticationResult(errors=[f'حدث خطأ أثناء إنشاء الحساب: {exc}'])

    def _validate(self, command: RegisterUserCommand) -> List[str]:
        errors: List[str] = []

        if not command.full_name:
            errors.append('يرجى إدخال الاسم')

        if not command.email:
            errors.append('يرجى إدخال البريد الإلكتروني')
        else:
            try:
                validate_email(command.email)
            except ValidationError:
                errors.append('يرجى إدخال بريد إلكتروني صحيح')

        if command.password != command.password_confirm:
            errors.append('كلمتا المرور غير متطابقتين')

        if command.email and User.objects.filter(email=command.email).exists():
            errors.append('البريد الإلكتروني مسجل مسبقاً')

        if command.tax_number and Organization.objects.filter(vat_number=command.tax_number).exists():
            errors.append('الرقم الضريبي مسجل مسبقاً')

        return errors


login_user_use_case = LoginUserUseCase()
register_user_use_case = RegisterUserUseCase()
