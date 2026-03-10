from core import monitoring_views as legacy_monitoring_views

from .base import OrganizationActionView


class MonitoringDashboardPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_monitoring_views.monitoring_dashboard_view(request, *args, **kwargs)


class ProcessingPipelinePageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_monitoring_views.processing_pipeline_view(request, *args, **kwargs)


class OCRMetricsPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_monitoring_views.ocr_metrics_view(request, *args, **kwargs)


class ComplianceReportPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_monitoring_views.compliance_report_view(request, *args, **kwargs)


class RiskDashboardPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_monitoring_views.risk_dashboard_view(request, *args, **kwargs)
