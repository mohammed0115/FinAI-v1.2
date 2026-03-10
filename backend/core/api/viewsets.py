import os

import requests
from django.conf import settings
from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.base import (
    BaseAuthenticatedModelViewSet,
    OrganizationScopedModelViewSet,
    OrganizationScopedReadOnlyModelViewSet,
)
from core.models import AuditLog, Configuration, Organization, User
from core.serializers import AuditLogSerializer, ConfigurationSerializer, OrganizationSerializer, UserSerializer


class UserViewSet(BaseAuthenticatedModelViewSet):
    queryset = User.objects.all().select_related('organization').order_by('email')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = self.get_base_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return queryset
        if getattr(user, 'organization_id', None):
            return queryset.filter(organization=user.organization)
        return queryset.filter(pk=user.pk)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def register(self, request):
        recaptcha_secret = getattr(settings, 'RECAPTCHA_SECRET_KEY', None) or os.environ.get('RECAPTCHA_SECRET_KEY')
        if recaptcha_secret:
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
                result = requests.post(verify_url, data=payload, timeout=5).json()
            except Exception:
                return Response({'recaptcha': 'reCAPTCHA verification failed.'}, status=status.HTTP_400_BAD_REQUEST)
            if not result.get('success'):
                return Response({'recaptcha': 'reCAPTCHA validation failed. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationViewSet(BaseAuthenticatedModelViewSet):
    queryset = Organization.objects.all().order_by('name')
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = self.get_base_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'admin':
            return queryset
        if getattr(user, 'organization_id', None):
            return queryset.filter(id=user.organization_id)
        return queryset.none()

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        org = self.get_object()

        from documents.models import Document, Transaction
        from reports.models import Insight, Report

        stats = {
            'total_documents': Document.objects.filter(organization=org).count(),
            'pending_documents': Document.objects.filter(organization=org, status='pending').count(),
            'total_transactions': Transaction.objects.filter(organization=org).count(),
            'unresolved_insights': Insight.objects.filter(organization=org, is_resolved=False).count(),
            'total_reports': Report.objects.filter(organization=org).count(),
            'users_count': User.objects.filter(organization=org).count(),
        }

        return Response(stats)


class AuditLogViewSet(OrganizationScopedReadOnlyModelViewSet):
    queryset = AuditLog.objects.all().select_related('organization', 'user').order_by('-created_at')
    serializer_class = AuditLogSerializer


class ConfigurationViewSet(OrganizationScopedModelViewSet):
    queryset = Configuration.objects.all().select_related('organization', 'updated_by').order_by('config_key')
    serializer_class = ConfigurationSerializer
    actor_save_field = 'updated_by'
    update_actor_save_field = 'updated_by'

    def get_global_access_filter(self):
        return Q(config_type='system')
