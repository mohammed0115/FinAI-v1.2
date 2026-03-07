"""Template tags for permission checks in Django templates.

Usage in templates:
    {% load permissions_tags %}
    
    {% if user|has_permission:'upload_document':'DOCUMENT' %}
        <button>Upload</button>
    {% endif %}
"""

from django import template
from core.permissions import check_permission, UserRole, PermissionMatrix

register = template.Library()


@register.filter(name='has_permission')
def has_permission(user, args):
    """Check if user has specific permission.
    
    Usage:
        {{ user|has_permission:'upload_document:DOCUMENT' }}
    """
    if not user or not user.is_authenticated:
        return False
    
    if ':' in args:
        permission, category = args.split(':', 1)
    else:
        permission = args
        category = 'DOCUMENT'
    
    return check_permission(user, permission, category)


@register.filter(name='has_role')
def has_role(user, role):
    """Check if user has specific role.
    
    Usage:
        {{ user|has_role:'admin' }}
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role == role


@register.filter(name='has_role_or_higher')
def has_role_or_higher(user, role):
    """Check if user has role or higher in hierarchy.
    
    Usage:
        {{ user|has_role_or_higher:'accountant' }}
    """
    if not user or not user.is_authenticated:
        return False
    
    return UserRole.has_higher_or_equal_role(user.role, role)


@register.simple_tag
def user_permissions(user):
    """Get all permissions for user.
    
    Usage:
        {% user_permissions user as perms %}
        {{ perms.DOCUMENT }}
    """
    if not user or not user.is_authenticated:
        return {}
    
    return PermissionMatrix.get_all_permissions_for_role(user.role)


@register.simple_tag
def can_access_feature(user, feature):
    """Check if user can access a major feature.
    
    Usage:
        {% can_access_feature user 'analytics' as can_access %}
        {% if can_access %}..{% endif %}
    """
    if not user or not user.is_authenticated:
        return False
    
    feature_permissions = {
        'analytics': ('view_analytics', 'ANALYTICS'),
        'reports': ('view_report', 'REPORT'),
        'documents': ('view_document', 'DOCUMENT'),
        'transactions': ('view_transaction', 'TRANSACTION'),
        'admin': ('*', 'USER'),
    }
    
    if feature not in feature_permissions:
        return False
    
    permission, category = feature_permissions[feature]
    
    if permission == '*':
        return user.role == UserRole.ADMIN
    
    return check_permission(user, permission, category)
