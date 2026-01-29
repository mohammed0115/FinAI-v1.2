from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReportViewSet, InsightViewSet

router = DefaultRouter()
router.register(r'reports', ReportViewSet)
router.register(r'insights', InsightViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
