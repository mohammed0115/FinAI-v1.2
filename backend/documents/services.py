"""Business logic layer for document management.

This module contains all business logic for document operations,
separated from views for better testability and reusability.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db import transaction
import uuid

from .models import Document, ExtractedData, Transaction
from core.models import User, Organization
from core.ai_service import ai_service


class DocumentService:
    """Service for document management operations."""
    
    @staticmethod
    def upload_document(
        file: UploadedFile,
        organization: Organization,
        uploaded_by: User,
        document_type: str = 'other'
    ) -> Document:
        """Upload and store a document.
        
        Args:
            file: The uploaded file
            organization: Organization the document belongs to
            uploaded_by: User who uploaded the document
            document_type: Type of document
            
        Returns:
            Created Document instance
            
        Raises:
            ValueError: If file is invalid
        """
        if not file:
            raise ValueError('No file provided')
        
        doc_id = uuid.uuid4()
        storage_key = f"documents/{organization.id}/{doc_id}/{file.name}"
        storage_path = default_storage.save(storage_key, file)
        storage_url = default_storage.url(storage_path)
        
        document = Document.objects.create(
            id=doc_id,
            organization=organization,
            uploaded_by=uploaded_by,
            file_name=file.name,
            file_type=file.content_type,
            file_size=file.size,
            storage_key=storage_key,
            storage_url=storage_url,
            document_type=document_type,
            status='pending'
        )
        
        return document
    
    @staticmethod
    def process_document(document: Document, image_url: str) -> Dict[str, Any]:
        """Process document with AI extraction.
        
        Args:
            document: Document to process
            image_url: Full URL to the document image
            
        Returns:
            Dict with processing results
            
        Raises:
            Exception: If processing fails
        """
        # Update status
        document.status = 'processing'
        document.save(update_fields=['status'])
        
        try:
            # Process with AI
            result = ai_service.process_document_with_vision(
                image_url=image_url,
                document_type=document.document_type
            )
            
            if not result.get('success'):
                document.status = 'failed'
                document.save(update_fields=['status'])
                raise Exception(result.get('error', 'Processing failed'))
            
            # Save extracted data in transaction
            with transaction.atomic():
                extracted_data = DocumentService._save_extracted_data(
                    document=document,
                    result=result
                )
                
                # Update document
                document.status = 'completed'
                document.language = result.get('language', 'en')
                document.is_handwritten = result.get('is_handwritten', False)
                document.processed_at = timezone.now()
                document.save()
            
            return {
                'success': True,
                'extracted_data_id': str(extracted_data.id),
                'confidence': result.get('confidence'),
                'language': result.get('language'),
                'is_handwritten': result.get('is_handwritten')
            }
            
        except Exception as e:
            document.status = 'failed'
            document.save(update_fields=['status'])
            raise
    
    @staticmethod
    def _save_extracted_data(document: Document, result: Dict[str, Any]) -> ExtractedData:
        """Save extracted data from AI processing."""
        structured_data = result.get('structured_data', {})
        extracted_text = result.get('extracted_text', {})
        
        # Helper to safely convert to Decimal
        def to_decimal(value) -> Optional[Decimal]:
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError):
                return None
        
        extracted_data = ExtractedData.objects.create(
            document=document,
            organization=document.organization,
            vendor_name=structured_data.get('vendorName'),
            customer_name=structured_data.get('customerName'),
            invoice_number=structured_data.get('invoiceNumber'),
            invoice_date=structured_data.get('invoiceDate'),
            due_date=structured_data.get('dueDate'),
            total_amount=to_decimal(structured_data.get('totalAmount')),
            tax_amount=to_decimal(structured_data.get('taxAmount')),
            currency=structured_data.get('currency'),
            items_json=structured_data.get('items'),
            raw_text_ar=extracted_text.get('arabic'),
            raw_text_en=extracted_text.get('english'),
            confidence=result.get('confidence', 0)
        )
        
        return extracted_data


class ExtractedDataService:
    """Service for extracted data validation."""
    
    @staticmethod
    def validate_data(
        extracted_data: ExtractedData,
        validated_by: User,
        validation_status: str = 'validated'
    ) -> ExtractedData:
        """Validate extracted data.
        
        Args:
            extracted_data: ExtractedData instance to validate
            validated_by: User performing validation
            validation_status: Status to set
            
        Returns:
            Updated ExtractedData instance
        """
        extracted_data.validation_status = validation_status
        extracted_data.validated_by = validated_by
        extracted_data.validated_at = timezone.now()
        extracted_data.save()
        
        return extracted_data


class TransactionService:
    """Service for transaction operations."""
    
    @staticmethod
    def reconcile_transaction(transaction: Transaction) -> Transaction:
        """Mark a transaction as reconciled.
        
        Args:
            transaction: Transaction to reconcile
            
        Returns:
            Updated Transaction instance
        """
        transaction.is_reconciled = True
        transaction.reconciled_at = timezone.now()
        transaction.save()
        
        return transaction
    
    @staticmethod
    def filter_by_date_range(
        queryset,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        """Filter transactions by date range."""
        if start_date and end_date:
            queryset = queryset.filter(transaction_date__range=[start_date, end_date])
        return queryset
    
    @staticmethod
    def filter_by_type(queryset, transaction_type: Optional[str] = None):
        """Filter transactions by type."""
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        return queryset
