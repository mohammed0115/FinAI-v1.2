from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from config.health_urls import health_check, ready_check
from django.http import JsonResponse

# Debug endpoint
def debug_auth(request):
    return JsonResponse({
        'authenticated': request.user.is_authenticated,
        'user': str(request.user),
        'session_key': request.session.session_key if hasattr(request, 'session') else None,
        'cookies': list(request.COOKIES.keys()),
    })

urlpatterns = [
    # Debug endpoint  
    path('debug-auth/', debug_auth, name='debug_auth'),
    
    # Health check endpoints (for Kubernetes)
    path('health', health_check, name='health_check'),
    path('health/', health_check, name='health_check_slash'),
    path('ready', ready_check, name='ready_check'),
    path('ready/', ready_check, name='ready_check_slash'),
    
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/core/', include('core.urls')),
    path('api/documents/', include('documents.urls')),
    path('api/analytics/', include('analytics.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/compliance/', include('compliance.urls')),
    
    # Web views
    path('', include('core.web_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
