from core.application.dashboard_queries import dashboard_snapshot_service
from core.views.base import OrganizationTemplateView


class DashboardPageView(OrganizationTemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(dashboard_snapshot_service.build(self.get_organization()))
        return context


dashboard_view = DashboardPageView.as_view()


__all__ = [
    'DashboardPageView',
    'dashboard_view',
]
