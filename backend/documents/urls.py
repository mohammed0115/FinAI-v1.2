from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet, ExtractedDataViewSet, TransactionViewSet,
    AccountViewSet, JournalEntryViewSet, ComplianceCheckViewSet, AuditFlagViewSet
)

router = DefaultRouter()
router.register(r'documents', DocumentViewSet)
router.register(r'extracted-data', ExtractedDataViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'accounts', AccountViewSet)
router.register(r'journal-entries', JournalEntryViewSet)
router.register(r'compliance-checks', ComplianceCheckViewSet)
router.register(r'audit-flags', AuditFlagViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
