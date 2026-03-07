from rest_framework import serializers
from .models import (
    Document, ExtractedData, Transaction, Account,
    JournalEntry, JournalEntryLine, ComplianceCheck, AuditFlag,
    InvoiceAuditFinding, AuditTrail
)
from core.serializers import UserSerializer


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.name', read_only=True)
    
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at', 'processed_at', 'storage_key', 'storage_url']


class ExtractedDataSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source='document.file_name', read_only=True)
    validated_by_name = serializers.CharField(source='validated_by.name', read_only=True)
    
    class Meta:
        model = ExtractedData
        fields = '__all__'
        read_only_fields = ['id', 'extracted_at', 'validated_at']


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TransactionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    document_name = serializers.CharField(source='document.file_name', read_only=True, allow_null=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'reconciled_at']


class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source='account.account_code', read_only=True)
    account_name = serializers.CharField(source='account.account_name', read_only=True)
    
    class Meta:
        model = JournalEntryLine
        fields = '__all__'
        read_only_fields = ['id']


class JournalEntrySerializer(serializers.ModelSerializer):
    lines = JournalEntryLineSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    posted_by_name = serializers.CharField(source='posted_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = JournalEntry
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'posted_at']


class ComplianceCheckSerializer(serializers.ModelSerializer):
    checked_by_name = serializers.CharField(source='checked_by.name', read_only=True, allow_null=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = ComplianceCheck
        fields = '__all__'
        read_only_fields = ['id', 'checked_at', 'resolved_at']


class AuditFlagSerializer(serializers.ModelSerializer):
    transaction_ref = serializers.CharField(source='transaction.reference_number', read_only=True, allow_null=True)
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditFlag
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'resolved_at']


class InvoiceAuditFindingSerializer(serializers.ModelSerializer):
    """Phase 2: Serializer for invoice audit findings"""
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = InvoiceAuditFinding
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class InvoiceReviewSerializer(serializers.Serializer):
    """Phase 2: Serializer for invoice review response"""
    id = serializers.UUIDField(read_only=True)
    document = serializers.SerializerMethodField()
    extracted_invoice = serializers.SerializerMethodField()
    normalized_invoice = serializers.JSONField(read_only=True)
    validation = serializers.SerializerMethodField()
    audit_findings = InvoiceAuditFindingSerializer(many=True, read_only=True)
    status = serializers.CharField(read_only=True)
    extracted_at = serializers.DateTimeField(read_only=True)
    
    def get_document(self, obj):
        return {
            'id': str(obj.document.id),
            'file_name': obj.document.file_name,
            'image_url': self.context.get('image_url'),
            'uploaded_at': obj.document.uploaded_at
        }
    
    def get_extracted_invoice(self, obj):
        return {
            'invoice_number': obj.invoice_number,
            'vendor_name': obj.vendor_name,
            'customer_name': obj.customer_name,
            'invoice_date': obj.invoice_date,
            'due_date': obj.due_date,
            'total_amount': obj.total_amount,
            'currency': obj.currency,
            'items': obj.items_json,
            'confidence': obj.confidence
        }
    
    def get_validation(self, obj):
        return {
            'is_valid': obj.is_valid,
            'completed_at': obj.validation_completed_at,
            'errors': obj.validation_errors or [],
            'warnings': obj.validation_warnings or []
        }


class AuditTrailSerializer(serializers.ModelSerializer):
    """Phase 3: Serializer for audit trail entries"""
    performed_by_name = serializers.CharField(source='performed_by.name', read_only=True, allow_null=True)
    
    class Meta:
        model = AuditTrail
        fields = '__all__'
        read_only_fields = ['id', 'event_time']
