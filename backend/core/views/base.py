from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView


class OrganizationAccessMixin:
    """Shared web-view behavior for authenticated tenant-aware pages."""

    login_url = 'login'
    require_authentication = True
    require_organization = True
    no_organization_template_name = 'no_organization.html'

    def get_organization(self):
        user = getattr(self.request, 'user', None)
        if user is None or not user.is_authenticated:
            return None
        return getattr(user, 'organization', None)

    def get_base_context(self, **kwargs):
        context = {
            'organization': self.get_organization(),
            'current_user': self.request.user,
        }
        context.update(kwargs)
        return context

    def handle_missing_organization(self):
        return render(
            self.request,
            self.no_organization_template_name,
            self.get_base_context(),
        )

    def dispatch(self, request, *args, **kwargs):
        if self.require_authentication and not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), self.login_url)
        if self.require_organization and request.user.is_authenticated and self.get_organization() is None:
            return self.handle_missing_organization()
        return super().dispatch(request, *args, **kwargs)


class OrganizationTemplateView(OrganizationAccessMixin, TemplateView):
    page_title = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for key, value in self.get_base_context().items():
            context.setdefault(key, value)
        if self.page_title:
            context.setdefault('page_title', self.page_title)
        return context


class OrganizationActionView(OrganizationAccessMixin, View):
    """Base class for command-style web views that render or redirect."""
