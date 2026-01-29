"""
Hard Rules API Views - واجهات برمجة التطبيقات للقواعد الصارمة

REST API endpoints for Hard Rules Engine.
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from decimal import Decimal
import logging

from .services import hard_rules_service
from .gate import hard_rules_gate

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_governance_status(request):
    """
    حالة الحوكمة - Governance Status
    
    Check if Hard Rules Engine is present and operational.
    This is the first step of governance validation.
    """
    try:
        status_data = hard_rules_service.get_governance_status()
        return Response(status_data)
    except Exception as e:
        logger.error(f"Governance status error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_rule_enforcement_summary(request):
    """
    ملخص إنفاذ القواعد - Rule Enforcement Summary
    
    Get summary of all enforced hard rules.
    """
    try:
        summary = hard_rules_service.get_rule_enforcement_summary()
        return Response(summary)
    except Exception as e:
        logger.error(f"Rule enforcement summary error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_invoice(request):
    """
    التحقق من الفاتورة - Invoice Validation
    
    Validate an invoice against all hard rules.
    
    Request body:
    {
        "invoice_data": {
            "invoice_number": "INV-001",
            "invoice_date": "2024-01-15",
            "party_name": "Customer Name",
            "total_amount": 1150.00,
            "subtotal": 1000.00,
            "vat_amount": 150.00,
            "currency": "SAR",
            "uuid": "...",
            ...
        },
        "country": "SA",
        "organization_id": "..."
    }
    """
    try:
        invoice_data = request.data.get('invoice_data', {})
        country = request.data.get('country', 'SA')
        organization_id = request.data.get('organization_id', '')
        
        # Get user info if authenticated
        user_id = str(request.user.id) if request.user.is_authenticated else 'anonymous'
        user_role = getattr(request.user, 'role', 'user') if request.user.is_authenticated else 'user'
        
        result = hard_rules_service.validate_invoice_with_logging(
            invoice_data=invoice_data,
            country=country,
            user_id=user_id,
            user_role=user_role,
            organization_id=organization_id,
        )
        
        return Response(result)
    except Exception as e:
        logger.error(f"Invoice validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_journal_entry(request):
    """
    التحقق من القيد اليومي - Journal Entry Validation
    
    Validate a journal entry against accounting rules.
    
    Request body:
    {
        "entry_id": "JE-001",
        "debit_amount": 1000.00,
        "credit_amount": 1000.00,
        "account_code": "1001",
        "transaction_type": "expense",
        "existing_accounts": {
            "1001": {"active": true, "type": "expense"}
        }
    }
    """
    try:
        entry_id = request.data.get('entry_id', 'unknown')
        debit_amount = Decimal(str(request.data.get('debit_amount', 0)))
        credit_amount = Decimal(str(request.data.get('credit_amount', 0)))
        account_code = request.data.get('account_code', '')
        transaction_type = request.data.get('transaction_type', '')
        existing_accounts = request.data.get('existing_accounts', {})
        organization_id = request.data.get('organization_id', '')
        
        user_id = str(request.user.id) if request.user.is_authenticated else 'anonymous'
        
        result = hard_rules_service.validate_journal_entry_with_logging(
            entry_id=entry_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            account_code=account_code,
            transaction_type=transaction_type,
            existing_accounts=existing_accounts,
            organization_id=organization_id,
            user_id=user_id,
        )
        
        return Response(result)
    except Exception as e:
        logger.error(f"Journal entry validation error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def check_ai_gate(request):
    """
    فحص بوابة الذكاء الاصطناعي - AI Gate Check
    
    Check if AI execution is allowed based on hard rules.
    
    Request body:
    {
        "ai_function_name": "analyze_invoice",
        "invoice_data": {...},  // Optional - if provided, validates first
        "organization_id": "..."
    }
    """
    try:
        ai_function_name = request.data.get('ai_function_name', 'unknown')
        invoice_data = request.data.get('invoice_data')
        organization_id = request.data.get('organization_id', '')
        country = request.data.get('country', 'SA')
        
        user_id = str(request.user.id) if request.user.is_authenticated else 'anonymous'
        
        result = hard_rules_service.check_ai_gate(
            ai_function_name=ai_function_name,
            invoice_data=invoice_data,
            organization_id=organization_id,
            user_id=user_id,
            country=country,
        )
        
        return Response(result)
    except Exception as e:
        logger.error(f"AI gate check error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_recent_evaluations(request):
    """
    التقييمات الأخيرة - Recent Evaluations
    
    Get recent Hard Rules evaluations.
    
    Query params:
    - organization_id: Filter by organization
    - limit: Number of results (default 50)
    """
    try:
        organization_id = request.query_params.get('organization_id')
        limit = int(request.query_params.get('limit', 50))
        
        evaluations = hard_rules_service.get_recent_evaluations(
            organization_id=organization_id,
            limit=limit
        )
        
        return Response({'evaluations': evaluations})
    except Exception as e:
        logger.error(f"Get evaluations error: {e}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_engine_health(request):
    """
    صحة المحرك - Engine Health Check
    
    Quick health check for the Hard Rules Engine.
    """
    try:
        engine_check = hard_rules_gate.check_engine_exists()
        
        return Response({
            'healthy': engine_check['exists'],
            'message': engine_check['message'],
            'message_ar': engine_check.get('message_ar', ''),
            'timestamp': hard_rules_service.get_governance_status().get('timestamp'),
        })
    except Exception as e:
        logger.error(f"Engine health check error: {e}")
        return Response(
            {
                'healthy': False,
                'error': str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
