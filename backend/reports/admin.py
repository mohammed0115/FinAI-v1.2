from django.contrib import admin
from .models import Report, Insight

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['report_name', 'report_type', 'status', 'organization', 'period_start', 'period_end']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['report_name', 'organization__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

@admin.register(Insight)
class InsightAdmin(admin.ModelAdmin):
    list_display = ['title', 'insight_type', 'severity', 'organization', 'is_resolved', 'created_at']
    list_filter = ['insight_type', 'severity', 'is_resolved', 'created_at']
    search_fields = ['title', 'description', 'organization__name']
    readonly_fields = ['id', 'created_at', 'resolved_at']
    date_hierarchy = 'created_at'
