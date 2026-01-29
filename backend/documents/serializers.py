from rest_framework import serializers
from .models import (
    Document, ExtractedData, Transaction, Account,
    JournalEntry, JournalEntryLine, ComplianceCheck, AuditFlag
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
