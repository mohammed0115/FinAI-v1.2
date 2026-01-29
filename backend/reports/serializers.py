from rest_framework import serializers
from .models import Report, Insight

class ReportSerializer(serializers.ModelSerializer):
    generated_by_name = serializers.CharField(source='generated_by.name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.name', read_only=True)
    
    class Meta:
        model = Report
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class InsightSerializer(serializers.ModelSerializer):
    resolved_by_name = serializers.CharField(source='resolved_by.name', read_only=True)
    
    class Meta:
        model = Insight
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'resolved_at']
