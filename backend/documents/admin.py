from django.contrib import admin
from .models import Document, ExtractedData, Transaction

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'document_type', 'status', 'organization', 'uploaded_by', 'uploaded_at']
    list_filter = ['status', 'document_type', 'language', 'is_handwritten']
    search_fields = ['file_name', 'organization__name', 'uploaded_by__email']
    readonly_fields = ['id', 'uploaded_at', 'processed_at']
    date_hierarchy = 'uploaded_at'

@admin.register(ExtractedData)
class ExtractedDataAdmin(admin.ModelAdmin):
    list_display = ['document', 'vendor_name', 'total_amount', 'currency', 'confidence', 'validation_status']
    list_filter = ['validation_status', 'currency']
    search_fields = ['vendor_name', 'customer_name', 'invoice_number']
    readonly_fields = ['id', 'extracted_at', 'validated_at']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_type', 'amount', 'currency', 'transaction_date', 'organization', 'is_reconciled']
    list_filter = ['transaction_type', 'currency', 'is_reconciled', 'transaction_date']
    search_fields = ['description', 'vendor_customer', 'category']
    readonly_fields = ['id', 'created_at', 'reconciled_at']
    date_hierarchy = 'transaction_date'
