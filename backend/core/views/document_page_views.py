from . import document_views as legacy_document_views
from .base import OrganizationActionView


class DocumentsListPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.documents_view(request, *args, **kwargs)


class DocumentUploadPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.document_upload_view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return legacy_document_views.document_upload_view(request, *args, **kwargs)


class ProcessPendingDocumentsView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.process_pending_documents(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return legacy_document_views.process_pending_documents(request, *args, **kwargs)


class OCREvidenceListPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.ocr_evidence_list_view(request, *args, **kwargs)


class OCREvidenceDetailPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.ocr_evidence_detail_view(request, *args, **kwargs)


class ReprocessWithAIView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.reprocess_with_ai_view(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return legacy_document_views.reprocess_with_ai_view(request, *args, **kwargs)


class PipelineResultPageView(OrganizationActionView):
    def get(self, request, *args, **kwargs):
        return legacy_document_views.pipeline_result_view(request, *args, **kwargs)


class PendingReviewSubmitView(OrganizationActionView):
    def post(self, request, *args, **kwargs):
        return legacy_document_views.pending_review_submit_view(request, *args, **kwargs)
