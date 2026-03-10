from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.api.viewsets import AuditLogViewSet, ConfigurationViewSet, OrganizationViewSet, UserViewSet
from core.monitoring_views import MonitoringViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'audit-logs', AuditLogViewSet)
router.register(r'configurations', ConfigurationViewSet)
router.register(r'monitoring', MonitoringViewSet, basename='monitoring')

urlpatterns = [
    path('', include(router.urls)),
]
