"""Health check endpoints for Kubernetes deployment."""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'finai-backend',
        'version': '1.0.0'
    }, status=200)

@csrf_exempt
@require_http_methods(["GET"])
def ready_check(request):
    """Readiness check endpoint."""
    # You can add additional checks here (database, cache, etc.)
    return JsonResponse({
        'status': 'ready',
        'service': 'finai-backend'
    }, status=200)
