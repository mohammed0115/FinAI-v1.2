from .base import *

DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1",
    "http://localhost",
]

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = None
