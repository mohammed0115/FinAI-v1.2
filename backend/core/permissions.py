"""Role-Based Access Control (RBAC) System for FinAI Platform.

This module implements a comprehensive permission system with:
- 5 distinct user roles
- Fine-grained action-based permissions
- Django REST Framework permission classes
- Decorator-based permission checks
"""

from rest_framework import permissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from functools import wraps
from django.core.exceptions import PermissionDenied


# ============================================================================
# ROLE DEFINITIONS
# ============================================================================

class UserRole:
    """Define all user roles in the system."""
    USER = 'user'
    AUDITOR = 'auditor'
    ACCOUNTANT = 'accountant'
    FINANCE_MANAGER = 'finance_manager'
    ADMIN = 'admin'
    
    CHOICES = [
        (USER, 'User'),
        (AUDITOR, 'Auditor'),
        (ACCOUNTANT, 'Accountant'),
        (FINANCE_MANAGER, 'Finance Manager'),
        (ADMIN, 'Admin'),
    ]
    
    @classmethod
    def get_hierarchy(cls):
        """Return role hierarchy (higher number = more permissions)."""
        return {
            cls.USER: 1,
            cls.AUDITOR: 2,
            cls.ACCOUNTANT: 3,
            cls.FINANCE_MANAGER: 4,
            cls.ADMIN: 5,
        }
    
    @classmethod
    def has_higher_or_equal_role(cls, user_role, required_role):
        """Check if user role is higher or equal to required role."""
        hierarchy = cls.get_hierarchy()
        return hierarchy.get(user_role, 0) >= hierarchy.get(required_role, 0)


# ============================================================================
# PERMISSION MATRIX
# ============================================================================

class PermissionMatrix:
    """Define what actions each role can perform."""
    
    # Document Permissions
    DOCUMENT_PERMISSIONS = {
        UserRole.USER: ['view_own_document', 'upload_document'],
        UserRole.AUDITOR: ['view_document', 'view_extracted_data', 'validate_data', 'view_audit_logs'],
        UserRole.ACCOUNTANT: ['view_document', 'upload_document', 'process_document', 'edit_extracted_data', 'validate_data'],
        UserRole.FINANCE_MANAGER: ['view_document', 'upload_document', 'process_document', 'edit_extracted_data', 'validate_data', 'delete_document'],
        UserRole.ADMIN: ['*'],  # All permissions
    }
    
    # Transaction Permissions
    TRANSACTION_PERMISSIONS = {
        UserRole.USER: ['view_own_transaction'],
        UserRole.AUDITOR: ['view_transaction', 'view_audit_logs'],
        UserRole.ACCOUNTANT: ['view_transaction', 'create_transaction', 'edit_transaction', 'reconcile_transaction'],
        UserRole.FINANCE_MANAGER: ['view_transaction', 'create_transaction', 'edit_transaction', 'delete_transaction', 'reconcile_transaction'],
        UserRole.ADMIN: ['*'],
    }
    
    # Report Permissions
    REPORT_PERMISSIONS = {
        UserRole.USER: [],
        UserRole.AUDITOR: ['view_report', 'generate_report'],
        UserRole.ACCOUNTANT: ['view_report', 'generate_report'],
        UserRole.FINANCE_MANAGER: ['view_report', 'generate_report', 'approve_report', 'submit_report'],
        UserRole.ADMIN: ['*'],
    }
    
    # Analytics Permissions
    ANALYTICS_PERMISSIONS = {
        UserRole.USER: [],
        UserRole.AUDITOR: ['view_analytics', 'view_insights'],
        UserRole.ACCOUNTANT: ['view_analytics', 'view_insights', 'generate_forecast'],
        UserRole.FINANCE_MANAGER: ['view_analytics', 'view_insights', 'generate_forecast', 'detect_anomalies', 'analyze_trends'],
        UserRole.ADMIN: ['*'],
    }
    
    # Organization Permissions
    ORGANIZATION_PERMISSIONS = {
        UserRole.USER: ['view_own_organization'],
        UserRole.AUDITOR: ['view_organization', 'view_configurations'],
        UserRole.ACCOUNTANT: ['view_organization', 'edit_configurations'],
        UserRole.FINANCE_MANAGER: ['view_organization', 'edit_organization', 'edit_configurations'],
        UserRole.ADMIN: ['*'],
    }
    
    # User Management Permissions
    USER_PERMISSIONS = {
        UserRole.USER: ['view_own_profile', 'edit_own_profile'],
        UserRole.AUDITOR: ['view_own_profile', 'edit_own_profile'],
        UserRole.ACCOUNTANT: ['view_own_profile', 'edit_own_profile', 'view_users'],
        UserRole.FINANCE_MANAGER: ['view_own_profile', 'edit_own_profile', 'view_users', 'create_user'],
        UserRole.ADMIN: ['*'],
    }
    
    @classmethod
    def has_permission(cls, role, permission, category='DOCUMENT'):
        """Check if role has specific permission in category."""
        permission_dict = getattr(cls, f'{category}_PERMISSIONS', {})
        role_permissions = permission_dict.get(role, [])
        
        # Admin has all permissions
        if '*' in role_permissions:
            return True
        
        return permission in role_permissions
    
    @classmethod
    def get_all_permissions_for_role(cls, role):
        """Get all permissions for a specific role."""
        all_permissions = {}
        
        for category in ['DOCUMENT', 'TRANSACTION', 'REPORT', 'ANALYTICS', 'ORGANIZATION', 'USER']:
            permission_dict = getattr(cls, f'{category}_PERMISSIONS', {})
            all_permissions[category] = permission_dict.get(role, [])
        
        return all_permissions


# ============================================================================
# DJANGO REST FRAMEWORK PERMISSION CLASSES
# ============================================================================

class IsOwnerOrHigherRole(permissions.BasePermission):
    """Permission: User can access only their own objects or has higher role."""
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role == UserRole.ADMIN:
            return True
        
        # Check if object belongs to user
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        
        if hasattr(obj, 'uploaded_by') and obj.uploaded_by == request.user:
            return True
        
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # Check if user has higher role
        return UserRole.has_higher_or_equal_role(
            request.user.role,
            UserRole.ACCOUNTANT
        )


class IsSameOrganization(permissions.BasePermission):
    """Permission: User can only access objects from their organization."""
    
    def has_object_permission(self, request, view, obj):
        # Admin can access all organizations
        if request.user.role == UserRole.ADMIN:
            return True
        
        # Check if object belongs to user's organization
        if hasattr(obj, 'organization'):
            return obj.organization == request.user.organization
        
        return False


class CanViewDocument(permissions.BasePermission):
    """Permission: Check if user can view documents."""
    
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return PermissionMatrix.has_permission(
                request.user.role,
                'view_document',
                'DOCUMENT'
            ) or request.user.role == UserRole.USER
        return True
    
    def has_object_permission(self, request, view, obj):
        # User can only view their own documents
        if request.user.role == UserRole.USER:
            return obj.uploaded_by == request.user
        
        # Others check permission and organization
        return (
            PermissionMatrix.has_permission(request.user.role, 'view_document', 'DOCUMENT') and
            obj.organization == request.user.organization
        )


class CanUploadDocument(permissions.BasePermission):
    """Permission: Check if user can upload documents."""
    
    def has_permission(self, request, view):
        if view.action in ['create', 'upload']:
            return PermissionMatrix.has_permission(
                request.user.role,
                'upload_document',
                'DOCUMENT'
            )
        return True


class CanProcessDocument(permissions.BasePermission):
    """Permission: Check if user can process documents with AI."""
    
    def has_permission(self, request, view):
        if view.action == 'process':
            return PermissionMatrix.has_permission(
                request.user.role,
                'process_document',
                'DOCUMENT'
            )
        return True


class CanManageTransactions(permissions.BasePermission):
    """Permission: Check transaction management permissions."""
    
    def has_permission(self, request, view):
        action_permission_map = {
            'list': 'view_transaction',
            'retrieve': 'view_transaction',
            'create': 'create_transaction',
            'update': 'edit_transaction',
            'partial_update': 'edit_transaction',
            'destroy': 'delete_transaction',
            'reconcile': 'reconcile_transaction',
        }
        
        permission = action_permission_map.get(view.action)
        if permission:
            return PermissionMatrix.has_permission(
                request.user.role,
                permission,
                'TRANSACTION'
            )
        return True


class CanGenerateReports(permissions.BasePermission):
    """Permission: Check if user can generate reports."""
    
    def has_permission(self, request, view):
        if view.action in ['create', 'generate']:
            return PermissionMatrix.has_permission(
                request.user.role,
                'generate_report',
                'REPORT'
            )
        return True


class CanApproveReports(permissions.BasePermission):
    """Permission: Check if user can approve reports."""
    
    def has_permission(self, request, view):
        if view.action == 'update_status':
            status = request.data.get('status')
            if status in ['approved', 'submitted']:
                return PermissionMatrix.has_permission(
                    request.user.role,
                    'approve_report',
                    'REPORT'
                )
        return True


class CanAccessAnalytics(permissions.BasePermission):
    """Permission: Check if user can access analytics."""
    
    def has_permission(self, request, view):
        action_permission_map = {
            'forecast': 'generate_forecast',
            'detect_anomalies': 'detect_anomalies',
            'analyze_trends': 'analyze_trends',
            'kpis': 'view_analytics',
        }
        
        permission = action_permission_map.get(view.action, 'view_analytics')
        return PermissionMatrix.has_permission(
            request.user.role,
            permission,
            'ANALYTICS'
        )


class CanManageUsers(permissions.BasePermission):
    """Permission: Check if user can manage other users."""
    
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            if request.user.role == UserRole.USER:
                # Users can only view their own profile
                return view.action == 'retrieve' and view.kwargs.get('pk') == str(request.user.id)
            return PermissionMatrix.has_permission(
                request.user.role,
                'view_users',
                'USER'
            )
        
        if view.action == 'create':
            return PermissionMatrix.has_permission(
                request.user.role,
                'create_user',
                'USER'
            )
        
        return True


# ============================================================================
# DECORATOR-BASED PERMISSION CHECKS
# ============================================================================

def require_role(required_role):
    """Decorator: Require specific role or higher to access view.
    
    Usage:
        @require_role(UserRole.ACCOUNTANT)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            if not UserRole.has_higher_or_equal_role(request.user.role, required_role):
                raise PermissionDenied(f"Role {required_role} or higher required")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_permission(permission, category='DOCUMENT'):
    """Decorator: Require specific permission to access view.
    
    Usage:
        @require_permission('process_document', 'DOCUMENT')
        def process_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            if not PermissionMatrix.has_permission(request.user.role, permission, category):
                raise PermissionDenied(f"Permission '{permission}' required")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_same_organization(get_object_func=None):
    """Decorator: Require user to be in same organization as object.
    
    Usage:
        @require_same_organization(lambda request, doc_id: Document.objects.get(id=doc_id))
        def my_view(request, doc_id):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            # Admin can access all organizations
            if request.user.role == UserRole.ADMIN:
                return view_func(request, *args, **kwargs)
            
            if get_object_func:
                obj = get_object_func(request, *args, **kwargs)
                if hasattr(obj, 'organization') and obj.organization != request.user.organization:
                    raise PermissionDenied("Access denied: Different organization")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def check_permission(user, permission, category='DOCUMENT'):
    """Helper function to check if user has permission.
    
    Args:
        user: User object
        permission: Permission string (e.g., 'view_document')
        category: Permission category (e.g., 'DOCUMENT')
    
    Returns:
        bool: True if user has permission
    """
    if not user or not user.is_authenticated:
        return False
    
    return PermissionMatrix.has_permission(user.role, permission, category)


def get_user_permissions(user):
    """Get all permissions for a user.
    
    Args:
        user: User object
    
    Returns:
        dict: Dictionary of all permissions by category
    """
    if not user or not user.is_authenticated:
        return {}
    
    return PermissionMatrix.get_all_permissions_for_role(user.role)


def can_access_organization_data(user, organization):
    """Check if user can access data from specific organization.
    
    Args:
        user: User object
        organization: Organization object
    
    Returns:
        bool: True if user can access
    """
    if not user or not user.is_authenticated:
        return False
    
    # Admin can access all organizations
    if user.role == UserRole.ADMIN:
        return True
    
    # User must be in same organization
    return user.organization == organization


def filter_queryset_by_organization(queryset, user):
    """Filter queryset to only show data from user's organization.
    
    Args:
        queryset: Django queryset
        user: User object
    
    Returns:
        Filtered queryset
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    
    # Admin can see all
    if user.role == UserRole.ADMIN:
        return queryset
    
    # Filter by organization
    if hasattr(queryset.model, 'organization'):
        return queryset.filter(organization=user.organization)
    
    return queryset
