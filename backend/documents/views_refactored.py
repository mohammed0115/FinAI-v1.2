"""Refactored views using service layer.

Views are now thin controllers that:
- Handle HTTP requests/responses
- Validate input
- Call service methods
- Return serialized data
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document, ExtractedData, Transaction
from .serializers import DocumentSerializer, ExtractedDataSerializer, TransactionSerializer
from .services import (
    DocumentService,
    ExtractedDataService,
    TransactionService
)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for document operations."""
    
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter documents based on user role and organization."""
        user = self.request.user
        if user.role == 'admin':
            return Document.objects.all()
        elif user.organization:
            return Document.objects.filter(organization=user.organization)
        return Document.objects.none()
    
    def perform_create(self, serializer):
        """Set uploaded_by to current user."""
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload a document."""
        file = request.FILES.get('file')
        organization_id = request.data.get('organization_id')
        document_type = request.data.get('document_type', 'other')
        
        try:
            # Use service to handle business logic
            document = DocumentService.upload_document(
                file=file,
                organization_id=organization_id,
                uploaded_by=request.user,
                document_type=document_type
            )
            
            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process document with AI."""
        document = self.get_object()
        image_url = request.build_absolute_uri(document.storage_url)
        
        try:
            # Use service for processing logic
            result = DocumentService.process_document(
                document=document,
                image_url=image_url
            )
            
            return Response(result)
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExtractedDataViewSet(viewsets.ModelViewSet):
    """ViewSet for extracted data operations."""
    
    queryset = ExtractedData.objects.all()
    serializer_class = ExtractedDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter extracted data based on user role and organization."""
        user = self.request.user
        if user.role == 'admin':
            return ExtractedData.objects.all()
        elif user.organization:
            return ExtractedData.objects.filter(organization=user.organization)
        return ExtractedData.objects.none()
    
    @action(detail=True, methods=['post'])
    def validate_data(self, request, pk=None):
        """Validate extracted data."""
        extracted = self.get_object()
        validation_status = request.data.get('status', 'validated')
        
        # Use service for business logic
        ExtractedDataService.validate_data(
            extracted_data=extracted,
            validated_by=request.user,
            validation_status=validation_status
        )
        
        serializer = self.get_serializer(extracted)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transaction operations."""
    
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter and sort transactions based on user and parameters."""
        user = self.request.user
        
        # Base queryset by role
        if user.role == 'admin':
            queryset = Transaction.objects.all()
        else:
            queryset = Transaction.objects.filter(organization=user.organization)
        
        # Apply filters using service methods
        queryset = TransactionService.filter_by_date_range(
            queryset,
            self.request.query_params.get('start_date'),
            self.request.query_params.get('end_date')
        )
        
        queryset = TransactionService.filter_by_type(
            queryset,
            self.request.query_params.get('type')
        )
        
        return queryset
    
    def perform_create(self, serializer):
        """Set created_by to current user."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark transaction as reconciled."""
        transaction = self.get_object()
        
        # Use service for business logic
        TransactionService.reconcile_transaction(transaction)
        
        serializer = self.get_serializer(transaction)
        return Response(serializer.data)
