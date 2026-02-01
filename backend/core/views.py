from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import User, Organization, AuditLog, Configuration
from .serializers import UserSerializer, OrganizationSerializer, AuditLogSerializer, ConfigurationSerializer
import os

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register new user with Google reCAPTCHA validation"""
        import requests
        from django.conf import settings

        # Get secret key from environment or settings
        recaptcha_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None) or os.environ.get('RECAPTCHA_SECRET_KEY')
        if recaptcha_secret:
            # If secret key is set, enforce reCAPTCHA
            recaptcha_token = request.data.get('g-recaptcha-response')
            if not recaptcha_token:
                return Response({'recaptcha': 'reCAPTCHA token is required.'}, status=status.HTTP_400_BAD_REQUEST)
            verify_url = 'https://www.google.com/recaptcha/api/siteverify'
            payload = {
                'secret': recaptcha_secret,
                'response': recaptcha_token,
                'remoteip': request.META.get('REMOTE_ADDR'),
            }
            try:
                r = requests.post(verify_url, data=payload, timeout=5)
                result = r.json()
            except Exception:
                return Response({'recaptcha': 'reCAPTCHA verification failed.'}, status=status.HTTP_400_BAD_REQUEST)
            if not result.get('success'):
                return Response({'recaptcha': 'reCAPTCHA validation failed. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)
        # If secret key is not set, skip reCAPTCHA (allow registration)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by('name')
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Organization.objects.all().order_by('name')
        elif user.organization:
            return Organization.objects.filter(id=user.organization.id).order_by('name')
        return Organization.objects.none()
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get organization statistics"""
        org = self.get_object()
        
        from documents.models import Document, Transaction
        from reports.models import Report, Insight
        
        stats = {
            'total_documents': Document.objects.filter(organization=org).count(),
            'pending_documents': Document.objects.filter(organization=org, status='pending').count(),
            'total_transactions': Transaction.objects.filter(organization=org).count(),
            'unresolved_insights': Insight.objects.filter(organization=org, is_resolved=False).count(),
            'total_reports': Report.objects.filter(organization=org).count(),
            'users_count': User.objects.filter(organization=org).count(),
        }
        
        return Response(stats)

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return AuditLog.objects.all()
        elif user.organization:
            return AuditLog.objects.filter(organization=user.organization)
        return AuditLog.objects.none()

class ConfigurationViewSet(viewsets.ModelViewSet):
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Configuration.objects.all()
        elif user.organization:
            return Configuration.objects.filter(Q(organization=user.organization) | Q(config_type='system'))
        return Configuration.objects.filter(config_type='system')
