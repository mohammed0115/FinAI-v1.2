"""
Compliance URLs - مسارات الامتثال
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegulatoryReferenceViewSet, ZATCAInvoiceViewSet,
    VATReconciliationViewSet, ZakatCalculationViewSet,
    AuditFindingViewSet, ComplianceDashboardViewSet,
    ZATCALiveVerificationViewSet
)

router = DefaultRouter()
router.register(r'regulatory-references', RegulatoryReferenceViewSet)
router.register(r'zatca-invoices', ZATCAInvoiceViewSet)
router.register(r'vat-reconciliations', VATReconciliationViewSet)
router.register(r'zakat-calculations', ZakatCalculationViewSet)
router.register(r'audit-findings', AuditFindingViewSet)
router.register(r'dashboard', ComplianceDashboardViewSet, basename='compliance-dashboard')
router.register(r'zatca-verification', ZATCALiveVerificationViewSet, basename='zatca-verification')

urlpatterns = [
    path('', include(router.urls)),
]
