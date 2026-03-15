"""
Documents services package.

Keep package imports lightweight so URL loading does not pull optional AI/PDF
dependencies into unrelated requests.
"""

from importlib import import_module

_EXPORTS = {
    'InvoiceAuditReportService': 'audit_report_service',
    'DataValidationService': 'audit_report_service',
    'DuplicateDetectionService': 'audit_report_service',
    'AnomalyDetectionService': 'audit_report_service',
    'RiskScoringService': 'audit_report_service',
    'RecommendationService': 'audit_report_service',
    'invoice_audit_workflow_service': 'audit_workflow_service',
    'invoice_ingestion_audit_service': 'ingestion_audit_service',
    'invoice_ingestion_persistence_service': 'ingestion_persistence_service',
    'OpenAIService': 'openai_service',
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')

    module = import_module(f'.{module_name}', __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
