# Load Celery app on Django startup so @shared_task decorators work correctly.
# Guard: if Celery is not installed (dev without Redis) we skip gracefully.
try:
    from .celery import app as celery_app  # noqa: F401
    __all__ = ('celery_app',)
except ImportError:
    pass
