"""
Celery Tasks — Application Layer async workers for FinAI.

These tasks offload heavy operations (OCR, pipeline) from the HTTP request cycle.
Each task follows SRP: one task, one job.

Usage from views:
    from core.tasks import run_ocr_pipeline, process_zip_batch
    run_ocr_pipeline.delay(document_id=str(doc.id))
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Task 1: OCR pipeline for a single document ────────────────────────────────

@shared_task(
    bind=True,
    name="core.tasks.run_ocr_pipeline",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def run_ocr_pipeline(self, document_id: str, language: str = "ara+eng",
                     is_handwritten: bool = False) -> dict:
    """
    Async wrapper for the full 5-phase invoice processing pipeline.

    Called after upload; document status is set to 'processing' before dispatch.
    On completion sets status to 'completed' or 'pending_review' / 'failed'.
    """
    from documents.models import Document, ExtractedData

    try:
        document = Document.objects.select_related('organization', 'uploaded_by').get(pk=document_id)
    except Document.DoesNotExist:
        logger.error("run_ocr_pipeline: document %s not found", document_id)
        return {"status": "not_found"}

    # Resolve physical file path
    file_path = document.storage_url
    if not os.path.isabs(file_path):
        from django.conf import settings
        file_path = os.path.join(settings.MEDIA_ROOT, file_path)

    if not os.path.exists(file_path):
        logger.error("run_ocr_pipeline: file missing at %s", file_path)
        document.status = 'failed'
        document.save(update_fields=['status'])
        return {"status": "file_missing"}

    try:
        from documents.views import DocumentViewSet
        view = DocumentViewSet()
        extracted = view._extract_invoice_data(document, file_path)

        confidence = extracted.confidence if extracted else 0
        if extracted and confidence < 40:
            document.status = 'pending_review'
        elif extracted:
            document.status = 'completed'
        else:
            document.status = 'failed'

        document.processed_at = timezone.now()
        document.save(update_fields=['status', 'processed_at'])

        logger.info("run_ocr_pipeline complete: doc=%s status=%s confidence=%s",
                    document_id, document.status, confidence)
        return {"status": document.status, "confidence": confidence}

    except Exception as exc:
        logger.exception("run_ocr_pipeline failed for doc %s: %s", document_id, exc)
        document.status = 'failed'
        document.save(update_fields=['status'])
        # Retry up to max_retries times
        raise self.retry(exc=exc)


# ── Task 2: Process a batch of pending documents ──────────────────────────────

@shared_task(name="core.tasks.process_pending_batch")
def process_pending_batch(organization_id: Optional[str] = None, limit: int = 20) -> dict:
    """
    Enqueue OCR pipeline tasks for all 'pending' documents.
    Can be scoped to a single organization or run globally.
    """
    from documents.models import Document

    qs = Document.objects.filter(status='pending')
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    qs = qs.order_by('uploaded_at')[:limit]

    dispatched = []
    for doc in qs:
        doc.status = 'processing'
        doc.save(update_fields=['status'])
        run_ocr_pipeline.delay(document_id=str(doc.id))
        dispatched.append(str(doc.id))

    logger.info("process_pending_batch: dispatched %d tasks", len(dispatched))
    return {"dispatched": len(dispatched), "ids": dispatched}


# ── Task 3: ZIP batch processing ──────────────────────────────────────────────

@shared_task(name="core.tasks.process_zip_documents")
def process_zip_documents(document_ids: List[str]) -> dict:
    """
    Process multiple documents extracted from a ZIP upload.
    Chains individual run_ocr_pipeline tasks for each document.
    """
    from celery import group

    job = group(run_ocr_pipeline.s(document_id=doc_id) for doc_id in document_ids)
    result = job.apply_async()
    logger.info("process_zip_documents: dispatched group of %d tasks", len(document_ids))
    return {"group_id": result.id if hasattr(result, 'id') else None, "count": len(document_ids)}
