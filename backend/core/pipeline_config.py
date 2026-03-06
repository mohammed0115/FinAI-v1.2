"""
Configuration Module for FinAI Invoice Processing Pipeline
Customize compliance thresholds, risk scoring, and performance settings
"""

import os
from decimal import Decimal

# ============================================================================
# PHASE 3: COMPLIANCE & RISK CONFIGURATION
# ============================================================================

class ComplianceConfig:
    """Customizable compliance check thresholds"""
    
    # Suspicious Discount Threshold (%)
    # Invoices with discounts above this % trigger a warning
    SUSPICIOUS_DISCOUNT_THRESHOLD = float(os.getenv('COMPLIANCE_DISCOUNT_THRESHOLD', '20.0'))
    
    # Large Invoice Threshold (SAR)
    # Invoices above this amount require additional review
    LARGE_INVOICE_THRESHOLD = Decimal(os.getenv('COMPLIANCE_LARGE_THRESHOLD', '100000'))
    
    # Very Large Invoice Threshold (SAR)
    # Invoices above this amount are flagged as critical
    VERY_LARGE_INVOICE_THRESHOLD = Decimal(os.getenv('COMPLIANCE_VERY_LARGE_THRESHOLD', '1000000'))
    
    # Risk Score Thresholds for Risk Levels
    RISK_LEVELS = {
        'low': (0, 25),
        'medium': (26, 50),
        'high': (51, 75),
        'critical': (76, 100),
    }
    
    # Tax Information Validation
    # Set to False to skip tax ID validation
    REQUIRE_TAX_ID = os.getenv('COMPLIANCE_REQUIRE_TAX_ID', 'true').lower() == 'true'
    
    # Payment Terms Validation (days)
    MIN_PAYMENT_DAYS = int(os.getenv('COMPLIANCE_MIN_PAYMENT_DAYS', '0'))
    MAX_PAYMENT_DAYS = int(os.getenv('COMPLIANCE_MAX_PAYMENT_DAYS', '180'))


# ============================================================================
# PHASE 4: CROSS-DOCUMENT INTELLIGENCE CONFIGURATION
# ============================================================================

class CrossDocumentConfig:
    """Customizable cross-document analysis thresholds"""
    
    # Duplicate Detection Thresholds
    EXACT_MATCH_THRESHOLD = float(os.getenv('DUPLICATE_EXACT_THRESHOLD', '0.99'))
    HIGH_SIMILARITY_THRESHOLD = float(os.getenv('DUPLICATE_HIGH_THRESHOLD', '0.85'))
    MEDIUM_SIMILARITY_THRESHOLD = float(os.getenv('DUPLICATE_MEDIUM_THRESHOLD', '0.70'))
    
    # Anomaly Detection Thresholds
    SUDDEN_SPIKE_RATIO = float(os.getenv('ANOMALY_SPIKE_RATIO', '2.0'))  # 200% increase
    LARGE_AMOUNT_THRESHOLD = Decimal(os.getenv('ANOMALY_LARGE_THRESHOLD', '500000'))
    
    # Stale Invoice Threshold (days)
    STALE_INVOICE_DAYS = int(os.getenv('ANOMALY_STALE_DAYS', '180'))
    
    # Rapid Invoicing Threshold (days)
    RAPID_INVOICING_RATIO = float(os.getenv('ANOMALY_RAPID_RATIO', '0.5'))


# ============================================================================
# PHASE 5: FINANCIAL INTELLIGENCE CONFIGURATION
# ============================================================================

class FinancialConfig:
    """Customizable financial intelligence settings"""
    
    # Cash Flow Forecast Period (days)
    FORECAST_PERIOD_DAYS = int(os.getenv('FORECAST_PERIOD_DAYS', '90'))
    
    # Spend Analysis Lookback Period (months)
    SPEND_ANALYSIS_MONTHS = int(os.getenv('SPEND_ANALYSIS_MONTHS', '12'))
    
    # Spending Trend Change Threshold (%)
    # Changes above this % are considered significant
    SPENDING_TREND_THRESHOLD = float(os.getenv('SPENDING_TREND_THRESHOLD', '10.0'))


# ============================================================================
# OPENAI CONFIGURATION
# ============================================================================

class OpenAIConfig:
    """OpenAI API configuration"""
    
    # API Key (from environment variable)
    API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Model Selection
    # Options: gpt-4, gpt-4-turbo, gpt-3.5-turbo
    EXTRACTION_MODEL = os.getenv('OPENAI_EXTRACTION_MODEL', 'gpt-4o-mini')
    NARRATIVE_MODEL = os.getenv('OPENAI_NARRATIVE_MODEL', 'gpt-3.5-turbo')
    
    # Temperature for narrative generation (0.0-1.0)
    # Higher = more creative, Lower = more deterministic
    NARRATIVE_TEMPERATURE = float(os.getenv('OPENAI_TEMPERATURE', '0.7'))
    
    # API Timeout (seconds)
    TIMEOUT = int(os.getenv('OPENAI_TIMEOUT', '30'))
    
    # Max retries on failure
    MAX_RETRIES = int(os.getenv('OPENAI_MAX_RETRIES', '3'))


# ============================================================================
# PERFORMANCE & MONITORING CONFIGURATION
# ============================================================================

class PerformanceConfig:
    """Performance monitoring and logging configuration"""
    
    # Enable performance profiling
    ENABLE_PROFILING = os.getenv('ENABLE_PROFILING', 'false').lower() == 'true'
    
    # Performance thresholds (seconds)
    EXTRACTION_TIMEOUT = float(os.getenv('EXTRACTION_TIMEOUT', '30.0'))
    PROCESSING_TIMEOUT = float(os.getenv('PROCESSING_TIMEOUT', '60.0'))
    
    # Slow query logging threshold (seconds)
    SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', '1.0'))
    
    # Enable detailed logging
    VERBOSE_LOGGING = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
    
    # Performance metrics storage
    STORE_METRICS = os.getenv('STORE_METRICS', 'true').lower() == 'true'


# ============================================================================
# CONFIGURATION CUSTOMIZATION GUIDE
# ============================================================================

"""
To customize configuration, set environment variables:

Example .env file:
------------------
# Compliance Settings
COMPLIANCE_DISCOUNT_THRESHOLD=15.0
COMPLIANCE_LARGE_THRESHOLD=50000
COMPLIANCE_REQUIRE_TAX_ID=true

# Duplicate Detection
DUPLICATE_EXACT_THRESHOLD=0.95
DUPLICATE_HIGH_THRESHOLD=0.80

# Anomaly Detection
ANOMALY_SPIKE_RATIO=3.0
ANOMALY_LARGE_THRESHOLD=1000000

# Financial Settings
FORECAST_PERIOD_DAYS=180
SPEND_ANALYSIS_MONTHS=24

# OpenAI Settings
OPENAI_EXTRACTION_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.5

# Performance
ENABLE_PROFILING=true
VERBOSE_LOGGING=true

Then start the application:
---
export $(cat .env | xargs) && python manage.py runserver
"""


def get_config():
    """Get unified configuration object"""
    return {
        'compliance': ComplianceConfig,
        'cross_document': CrossDocumentConfig,
        'financial': FinancialConfig,
        'openai': OpenAIConfig,
        'performance': PerformanceConfig,
    }


def print_config_summary():
    """Print current configuration for debugging"""
    print("\n" + "="*70)
    print("FinAI CONFIGURATION SUMMARY")
    print("="*70)
    
    print("\n[COMPLIANCE]")
    print(f"  Suspicious Discount Threshold: {ComplianceConfig.SUSPICIOUS_DISCOUNT_THRESHOLD}%")
    print(f"  Large Invoice Threshold: {ComplianceConfig.LARGE_INVOICE_THRESHOLD} SAR")
    print(f"  Very Large Threshold: {ComplianceConfig.VERY_LARGE_INVOICE_THRESHOLD} SAR")
    print(f"  Require Tax ID: {ComplianceConfig.REQUIRE_TAX_ID}")
    print(f"  Allow Payment Days: {ComplianceConfig.MIN_PAYMENT_DAYS}-{ComplianceConfig.MAX_PAYMENT_DAYS}")
    
    print("\n[CROSS-DOCUMENT]")
    print(f"  Exact Duplicate Match: {CrossDocumentConfig.EXACT_MATCH_THRESHOLD}")
    print(f"  High Similarity: {CrossDocumentConfig.HIGH_SIMILARITY_THRESHOLD}")
    print(f"  Spike Detection: {CrossDocumentConfig.SUDDEN_SPIKE_RATIO}x")
    print(f"  Stale Invoice (days): {CrossDocumentConfig.STALE_INVOICE_DAYS}")
    
    print("\n[FINANCIAL INTELLIGENCE]")
    print(f"  Forecast Period: {FinancialConfig.FORECAST_PERIOD_DAYS} days")
    print(f"  Spend Analysis: {FinancialConfig.SPEND_ANALYSIS_MONTHS} months")
    print(f"  Trend Threshold: {FinancialConfig.SPENDING_TREND_THRESHOLD}%")
    
    print("\n[OPENAI]")
    print(f"  Extraction Model: {OpenAIConfig.EXTRACTION_MODEL}")
    print(f"  Narrative Model: {OpenAIConfig.NARRATIVE_MODEL}")
    print(f"  Temperature: {OpenAIConfig.NARRATIVE_TEMPERATURE}")
    print(f"  Timeout: {OpenAIConfig.TIMEOUT}s")
    
    print("\n[PERFORMANCE]")
    print(f"  Profiling Enabled: {PerformanceConfig.ENABLE_PROFILING}")
    print(f"  Extraction Timeout: {PerformanceConfig.EXTRACTION_TIMEOUT}s")
    print(f"  Processing Timeout: {PerformanceConfig.PROCESSING_TIMEOUT}s")
    print(f"  Verbose Logging: {PerformanceConfig.VERBOSE_LOGGING}")
    
    print("\n" + "="*70 + "\n")
