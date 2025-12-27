from django.contrib import admin
from config.admin import admin_site
from .models import Notification, TelegramConfig, NotificationTemplate


@admin.register(Notification, site=admin_site)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'channel', 'status', 'sent_at', 'created_at']
    list_filter = ['channel', 'status', 'created_at']
    search_fields = ['partner__name', 'subject', 'message', 'recipient']
    readonly_fields = ['sent_at', 'error_message', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self, request):
        """Оптимизированный queryset с prefetch"""
        qs = super().get_queryset(request)
        return qs.select_related('partner')


@admin.register(TelegramConfig, site=admin_site)
class TelegramConfigAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'is_active', 'is_default', 'created_at']
    list_filter = ['is_active', 'is_default', 'created_at']
    search_fields = ['partner__name', 'partner__inn']
    readonly_fields = ['created_at', 'updated_at', 'validated_at']
    ordering = ['-created_at']

    def get_queryset(self, request):
        """Оптимизированный queryset с prefetch"""
        qs = super().get_queryset(request)
        return qs.select_related('partner')


@admin.register(NotificationTemplate, site=admin_site)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name', 'is_active']
    list_filter = ['is_active', 'code']
    search_fields = ['name', 'code', 'subject_template', 'message_template']
    ordering = ['code']