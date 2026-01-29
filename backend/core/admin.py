from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Organization, AuditLog, Configuration

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'name', 'role', 'organization', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'organization']
    search_fields = ['email', 'name']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'role', 'organization')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_signed_in', 'created_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'role', 'organization'),
        }),
    )
    
    readonly_fields = ['created_at', 'last_signed_in']

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'company_type', 'currency', 'vat_rate', 'created_at']
    list_filter = ['country', 'company_type']
    search_fields = ['name', 'tax_id']
    readonly_fields = ['id', 'created_at', 'updated_at']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'entity_type', 'organization', 'created_at']
    list_filter = ['action', 'entity_type', 'created_at']
    search_fields = ['user__email', 'action', 'entity_type']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    list_display = ['config_key', 'config_type', 'organization', 'updated_at']
    list_filter = ['config_type']
    search_fields = ['config_key', 'config_value']
    readonly_fields = ['id', 'updated_at']
