"""
ASGI application entry point for deployment.
Configures Django settings and provides the ASGI application for uvicorn.
"""
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Load environment variables
from dotenv import load_dotenv
load_dotenv(BASE_DIR / '.env')

# Setup Django before importing any Django modules
import django
django.setup()

# Import Django ASGI application
from django.core.asgi import get_asgi_application

# Create the ASGI application
application = get_asgi_application()

# Alias for uvicorn
app = application
