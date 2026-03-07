from django.contrib import admin
from .models import AIPluginSetting

@admin.register(AIPluginSetting)
class AIPluginSettingAdmin(admin.ModelAdmin):
    list_display = ("plugin_code", "provider", "is_enabled", "updated_at")
    search_fields = ("plugin_code",)
    list_filter = ("provider", "is_enabled")