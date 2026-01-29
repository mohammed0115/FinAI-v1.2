from django.urls import path
from .views import AnalyticsViewSet

analytics_viewset = AnalyticsViewSet.as_view({
    'post': 'forecast',
})

urlpatterns = [
    path('forecast/', AnalyticsViewSet.as_view({'post': 'forecast'}), name='forecast'),
    path('detect-anomalies/', AnalyticsViewSet.as_view({'post': 'detect_anomalies'}), name='detect-anomalies'),
    path('analyze-trends/', AnalyticsViewSet.as_view({'post': 'analyze_trends'}), name='analyze-trends'),
    path('generate-insights/', AnalyticsViewSet.as_view({'post': 'generate_insights'}), name='generate-insights'),
    path('kpis/', AnalyticsViewSet.as_view({'get': 'kpis'}), name='kpis'),
]
