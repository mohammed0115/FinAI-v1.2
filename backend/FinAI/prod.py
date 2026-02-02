from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "tadgeeg.com",
    "www.tadgeeg.com",
    "72.62.239.220",
]

CSRF_TRUSTED_ORIGINS = [
    "https://tadgeeg.com",
    "https://www.tadgeeg.com",
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "https://tadgeeg.com",
    "https://www.tadgeeg.com",
]
