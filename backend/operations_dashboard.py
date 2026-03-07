#!/usr/bin/env python
"""
FinAI Operations Dashboard - Real-time monitoring and health checks

Provides comprehensive view of system health, performance, and invoice processing status.
"""

import os
import sys
import django
from datetime import datetime, timedelta
from collections import defaultdict

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FinAI.settings')
django.setup()

from documents.models import Document, ExtractedData
from core.models import Organization
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Sum, Q
from django.utils import timezone
from core.performance_monitor import PerformanceMetrics

User = get_user_model()


class FinAIOperationsDashboard:
    """Real-time operations monitoring for FinAI system"""
    
    def __init__(self):
        self.start_time = datetime.now()
    
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "█" * 80)
        print(f"█  {text:<76}█")
        print("█" * 80)
    
    def print_section(self, title):
        """Print section header"""
        print(f"\n┌─ {title} {'─' * (75 - len(title))}")
    
    def print_stat(self, label, value, unit="", warning_threshold=None):
        """Print statistic with optional warning"""
        warning = ""
        if warning_threshold and isinstance(value, (int, float)):
            if value > warning_threshold:
                warning = " ⚠️  WARNING"
        
        print(f"   {label:<35} │ {str(value):<15} {unit}{warning}")
    
    def get_database_stats(self):
        """Get database statistics"""
        self.print_section("DATABASE STATISTICS")
        
        # Document counts
        total_docs = Document.objects.count()
        pending_docs = Document.objects.filter(
            extracted_data__extraction_status__isnull=True
        ).count()
        completed_docs = Document.objects.filter(
            extracted_data__extraction_status='completed'
        ).count()
        failed_docs = Document.objects.filter(
            extracted_data__extraction_status='error'
        ).count()
        
        self.print_stat("Total Documents", total_docs)
        self.print_stat("Completed", completed_docs)
        self.print_stat("Processing", pending_docs, warning_threshold=5)
        self.print_stat("Failed", failed_docs, warning_threshold=1)
        
        # Invoice value statistics
        extracted_stats = ExtractedData.objects.aggregate(
            total_value=Sum('total_amount'),
            avg_value=Avg('total_amount'),
            count=Count('id')
        )
        
        self.print_stat(
            "Total Invoice Value",
            f"{extracted_stats['total_value'] or 0:,.0f}" if extracted_stats['total_value'] else 0,
            "SAR"
        )
        self.print_stat(
            "Average Invoice Value",
            f"{extracted_stats['avg_value'] or 0:,.0f}" if extracted_stats['avg_value'] else 0,
            "SAR"
        )
        
        return {
            'total': total_docs,
            'completed': completed_docs,
            'pending': pending_docs,
            'failed': failed_docs
        }
    
    def get_processing_quality(self):
        """Get processing quality metrics"""
        self.print_section("PROCESSING QUALITY")
        
        extracted_data = ExtractedData.objects.all()
        
        if extracted_data.count() == 0:
            print("   No processed invoices yet")
            return {}
        
        # Confidence scores
        avg_confidence = extracted_data.aggregate(Avg('confidence'))['confidence__avg'] or 0
        high_confidence = extracted_data.filter(confidence__gte=90).count()
        low_confidence = extracted_data.filter(confidence__lt=70).count()
        
        # Validation
        valid_count = extracted_data.filter(is_valid=True).count()
        validation_rate = (valid_count / extracted_data.count() * 100) if extracted_data.exists() else 0
        
        # Risk assessment
        avg_risk = extracted_data.aggregate(Avg('risk_score'))['risk_score__avg'] or 0
        high_risk = extracted_data.filter(risk_score__gte=70).count()
        low_risk = extracted_data.filter(risk_score__lt=30).count()
        
        self.print_stat("Avg Extraction Confidence", f"{avg_confidence:.1f}%")
        self.print_stat("High Confidence (>90%)", high_confidence)
        self.print_stat("Low Confidence (<70%)", low_confidence, warning_threshold=3)
        
        print()
        
        self.print_stat("Validation Rate", f"{validation_rate:.1f}%")
        self.print_stat("Valid Invoices", valid_count)
        self.print_stat("Invalid Invoices", extracted_data.filter(is_valid=False).count())
        
        print()
        
        self.print_stat("Avg Risk Score", f"{avg_risk:.1f}/100")
        self.print_stat("High Risk (>70)", high_risk, warning_threshold=5)
        self.print_stat("Low Risk (<30)", low_risk)
        
        return {
            'avg_confidence': avg_confidence,
            'validation_rate': validation_rate,
            'avg_risk': avg_risk
        }
    
    def get_compliance_status(self):
        """Get compliance metrics"""
        self.print_section("COMPLIANCE STATUS")
        
        extracted_data = ExtractedData.objects.all()
        
        if extracted_data.count() == 0:
            print("   No compliance data yet")
            return {}
        
        # Risk distribution
        critical_risk = extracted_data.filter(risk_level='critical').count()
        high_risk = extracted_data.filter(risk_level='high').count()
        medium_risk = extracted_data.filter(risk_level='medium').count()
        low_risk = extracted_data.filter(risk_level='low').count()
        
        # Compliance issues (simplified for SQLite compatibility)
        with_discount_issues = 0
        with_tax_issues = 0
        
        # Overall compliance rate
        total = extracted_data.count()
        compliant = extracted_data.filter(risk_level='low').count()
        compliance_rate = (compliant / total * 100) if total > 0 else 0
        
        self.print_stat("Risk Level - Critical", critical_risk, warning_threshold=1)
        self.print_stat("Risk Level - High", high_risk, warning_threshold=5)
        self.print_stat("Risk Level - Medium", medium_risk)
        self.print_stat("Risk Level - Low", low_risk)
        
        print()
        
        self.print_stat("Overall Compliance Rate", f"{compliance_rate:.1f}%")
        self.print_stat("Invoices with Discount Issues", with_discount_issues)
        self.print_stat("Invoices with Tax Issues", with_tax_issues)
        
        return {
            'compliance_rate': compliance_rate,
            'high_risk': critical_risk + high_risk
        }
    
    def get_performance_metrics(self):
        """Get system performance metrics"""
        self.print_section("PERFORMANCE METRICS")
        
        stats = PerformanceMetrics.get_all_stats()
        
        if not stats:
            print("   No performance data collected yet")
            print("   Enable: export PERFORMANCE_ENABLE_PROFILING=True")
            return {}
        
        print("\n   Phase Execution Times:")
        phases = ['extraction', 'normalization', 'compliance_check', 
                  'cross_document', 'financial_intelligence']
        
        for phase in phases:
            if phase in stats:
                metric = stats[phase]
                avg_time = metric.get('avg', 0)
                status = "✓" if avg_time < 10 else "⚠"
                print(f"   {status} Phase {phase:<25} │ {avg_time:>6.2f}s avg")
        
        # Overall throughput
        total_processed = sum(s.get('count', 0) for s in stats.values())
        self.print_stat(
            "Total Invoices Processed",
            total_processed
        )
        
        return stats
    
    def get_crosdoc_analysis(self):
        """Get cross-document analysis results"""
        self.print_section("CROSS-DOCUMENT ANALYSIS")
        
        extracted_data = ExtractedData.objects.all()
        
        if extracted_data.count() == 0:
            print("   No cross-document data yet")
            return {}
        
        # Duplicate detection (simplified for SQLite)
        exact_duplicates = 0
        high_similarity = 0
        
        # Anomalies (simplified - exclude null values)
        with_anomalies = extracted_data.exclude(
            anomaly_flags__isnull=True
        ).count()
        
        # Vendor risk
        vendor_risk_high = extracted_data.filter(vendor_risk_level='high').count()
        vendor_risk_medium = extracted_data.filter(vendor_risk_level='medium').count()
        
        self.print_stat("Exact Duplicates Detected", exact_duplicates)
        self.print_stat("High Similarity Found", high_similarity)
        self.print_stat("Invoices with Anomalies", with_anomalies)
        
        print()
        
        self.print_stat("Vendor Risk - High", vendor_risk_high, warning_threshold=3)
        self.print_stat("Vendor Risk - Medium", vendor_risk_medium)
        
        # Top vendors
        vendor_stats = extracted_data.values('vendor_name').annotate(
            count=Count('id'),
            avg_amount=Avg('total_amount')
        ).order_by('-count')[:5]
        
        if vendor_stats:
            print("\n   Top Vendors:")
            for vendor in vendor_stats:
                print(f"     • {vendor['vendor_name']:<30} │ "
                      f"{vendor['count']:>3} invoices │ "
                      f"Avg: {vendor['avg_amount']:>10,.0f} SAR")
        
        return {
            'duplicates': exact_duplicates,
            'anomalies': with_anomalies
        }
    
    def get_financial_summary(self):
        """Get financial intelligence summary"""
        self.print_section("FINANCIAL INTELLIGENCE")
        
        extracted_data = ExtractedData.objects.all()
        
        if extracted_data.count() == 0:
            print("   No financial data yet")
            return {}
        
        # Spending trends (using invoice_date field)
        last_30_days = datetime.now() - timedelta(days=30)
        
        # Safely get spending - handle null dates
        invoices_this_month = extracted_data.filter(
            invoice_date__isnull=False,
            invoice_date__gte=last_30_days.date()
        )
        spending_30d = invoices_this_month.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Last 90 days
        last_90_days = datetime.now() - timedelta(days=90)
        invoices_90d = extracted_data.filter(
            invoice_date__isnull=False,
            invoice_date__gte=last_90_days.date()
        )
        spending_90d = invoices_90d.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # Payment terms analysis
        due_soon = extracted_data.filter(
            due_date__lte=datetime.now().date() + timedelta(days=7),
            due_date__gte=datetime.now().date()
        ).count()
        
        overdue = extracted_data.filter(
            due_date__lt=datetime.now().date()
        ).count()
        
        self.print_stat("Spending (Last 30 Days)", f"{spending_30d:,.0f}", "SAR")
        self.print_stat("Spending (Last 90 Days)", f"{spending_90d:,.0f}", "SAR")
        
        print()
        
        self.print_stat("Invoices Due Soon (7 days)", due_soon)
        self.print_stat("Overdue Invoices", overdue, warning_threshold=1)
        
        return {
            'spending_30d': spending_30d,
            'spending_90d': spending_90d,
            'overdue': overdue
        }
    
    def get_system_health(self):
        """Get overall system health"""
        self.print_section("SYSTEM HEALTH")
        
        try:
            # Database check
            doc_count = Document.objects.count()
            db_status = "✓ OK"
        except Exception as e:
            db_status = f"✗ ERROR: {e}"
            doc_count = 0
        
        # API check
        try:
            from core.openai_invoice_extraction_service import get_openai_extraction_service
            api_status = "✓ OK"
        except Exception as e:
            api_status = f"✗ ERROR: {e}"
        
        # Storage check
        try:
            media_path = "/home/mohamed/FinAI-v1.2/backend/media"
            if os.path.exists(media_path):
                size_mb = sum(os.path.getsize(f) for f in 
                             os.path.walk(media_path)) / 1024 / 1024
                storage_status = f"✓ {size_mb:.1f} MB used"
            else:
                storage_status = "✓ No media files yet"
        except Exception as e:
            storage_status = f"✗ ERROR: {e}"
        
        print(f"   Database Connection      │ {db_status}")
        print(f"   OpenAI API Status        │ {api_status}")
        print(f"   Media Storage            │ {storage_status}")
        
        # Environment check
        env_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'DEBUG': os.getenv('DEBUG', 'Not set'),
        }
        
        print("\n   Configuration:")
        for var, value in env_vars.items():
            if value:
                display = '***' if 'KEY' in var else value
                print(f"      {var:<20} = {display}")
        
        return {
            'database': 'OK' in db_status,
            'api': 'OK' in api_status
        }
    
    def get_user_activity(self):
        """Get user activity summary"""
        self.print_section("USER ACTIVITY")
        
        total_users = User.objects.count()
        active_users = User.objects.filter(last_login__isnull=False).count()
        
        organizations = Organization.objects.count()
        
        # Recent uploads
        last_24h = timezone.now() - timedelta(hours=24)
        recent_uploads = Document.objects.filter(
            created_at__gte=last_24h
        ).count()
        
        self.print_stat("Total Users", total_users)
        self.print_stat("Active Users", active_users)
        self.print_stat("Organizations", organizations)
        self.print_stat("Uploads (Last 24h)", recent_uploads)
        
        return {
            'active_users': active_users,
            'recent_uploads': recent_uploads
        }
    
    def print_alerts(self, stats):
        """Print active alerts based on statistics"""
        self.print_section("ACTIVE ALERTS")
        
        alerts = []
        
        # Database alerts
        if stats.get('database', {}).get('failed', 0) > 0:
            alerts.append("⚠️  Failed document processing detected")
        
        if stats.get('database', {}).get('pending', 0) > 10:
            alerts.append("⚠️  Large processing queue - may indicate slowness")
        
        # Quality alerts
        if stats.get('quality', {}).get('validation_rate', 100) < 80:
            alerts.append("⚠️  Low validation rate - check data quality")
        
        # Compliance alerts
        if stats.get('compliance', {}).get('high_risk', 0) > 10:
            alerts.append("⚠️  High number of high-risk invoices")
        
        # Cross-document alerts
        if stats.get('crosdoc', {}).get('duplicates', 0) > 5:
            alerts.append("⚠️  Multiple duplicates detected - review invoicing process")
        
        # Financial alerts
        if stats.get('financial', {}).get('overdue', 0) > 0:
            alerts.append(f"⚠️  {stats['financial']['overdue']} overdue invoices")
        
        if not alerts:
            print("   ✓ No active alerts")
        else:
            for i, alert in enumerate(alerts, 1):
                print(f"   {i}. {alert}")
        
        return alerts
    
    def run_dashboard(self):
        """Run complete operations dashboard"""
        self.print_header("FINAI OPERATIONS DASHBOARD")
        
        print(f"\n   Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Environment: {'Production' if not os.getenv('DEBUG') else 'Development'}")
        
        # Collect statistics
        stats = {
            'database': self.get_database_stats(),
            'quality': self.get_processing_quality(),
            'compliance': self.get_compliance_status(),
            'performance': self.get_performance_metrics(),
            'crosdoc': self.get_crosdoc_analysis(),
            'financial': self.get_financial_summary(),
            'system': self.get_system_health(),
            'users': self.get_user_activity(),
        }
        
        # Alerts
        self.print_alerts(stats)
        
        # Footer
        print("\n" + "█" * 80)
        print("█" * 80 + "\n")
        
        # Recommendations
        self.print_section("RECOMMENDATIONS")
        
        db_stats = stats.get('database', {})
        quality_stats = stats.get('quality', {})
        compliance_stats = stats.get('compliance', {})
        
        if db_stats.get('pending', 0) > 0:
            print("   1. Monitor processing queue - consider scaling if > 20")
        
        if quality_stats.get('validation_rate', 100) < 80:
            print("   2. Review data quality - investigate low validation rates")
        
        if db_stats.get('failed', 0) > 0:
            print("   3. Check failed documents - review corruption or format issues")
        
        if compliance_stats.get('high_risk', 0) > db_stats.get('total', 1) * 0.2:
            print("   4. Review compliance thresholds - too many high-risk invoices")
        
        print("\n" + "█" * 80 + "\n")
    
    def export_report(self, filename):
        """Export dashboard to JSON"""
        import json
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'database': self.get_database_stats(),
            'quality': self.get_processing_quality(),
            'compliance': self.get_compliance_status(),
            'financial': self.get_financial_summary(),
        }
        
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        print(f"✓ Report exported to {filename}")


if __name__ == '__main__':
    dashboard = FinAIOperationsDashboard()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--export':
        filename = sys.argv[2] if len(sys.argv) > 2 else 'finai_report.json'
        dashboard.export_report(filename)
    else:
        dashboard.run_dashboard()
