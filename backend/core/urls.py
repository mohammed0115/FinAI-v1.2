from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, OrganizationViewSet, AuditLogViewSet, ConfigurationViewSet
from .monitoring_views import MonitoringViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'organizations', OrganizationViewSet)
router.register(r'audit-logs', AuditLogViewSet)
router.register(r'configurations', ConfigurationViewSet)
router.register(r'monitoring', MonitoringViewSet, basename='monitoring')

urlpatterns = [
    path('', include(router.urls)),
]
