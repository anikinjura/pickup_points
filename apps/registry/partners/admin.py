# apps/registry/partners/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from config.admin import admin_site
from .models import Partner, PartnerMember, PartnerApplication, PickupPoint

from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.admin import TokenAdmin

from .services.partner_service import approve_partner_application, reject_partner_application

# Регистрируем стандартные административные классы с кастомной админкой
@admin.register(User, site=admin_site)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_display_links = ('id', 'username')  # Сделаем ID и username кликабельными
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'date_joined')
    search_fields = ('username', 'first_name', 'last_name', 'email')

@admin.register(Group, site=admin_site)
class GroupAdmin(GroupAdmin):
    pass  # Используем стандартный GroupAdmin

@admin.register(Permission, site=admin_site)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'content_type', 'codename']
    list_filter = ['content_type']

@admin.register(Token, site=admin_site)
class TokenAdmin(TokenAdmin):
    list_display = ['key', 'user', 'created']
    list_filter = ['created']
    search_fields = ['user__username', 'user__email', 'key']

@admin.register(PartnerApplication, site=admin_site)
class PartnerApplicationAdmin(admin.ModelAdmin):
    list_display = ['id', 'company_name', 'user', 'inn', 'status', 'get_processed_by', 'created_at']
    list_filter = [
        'status',
        ('created_at', admin.DateFieldListFilter),
        ('processed_at', admin.DateFieldListFilter),
        'user'
    ]
    search_fields = ['company_name', 'inn', 'ogrn', 'contact_email', 'contact_phone', 'user__username', 'user__email']
    list_select_related = ['user', 'processed_by']
    readonly_fields = ['created_at', 'updated_at', 'processed_at', 'processed_by', 'rejection_reason']

    fieldsets = (
        (None, {
            'fields': ('user', 'status')
        }),
        (_('Информация о компании'), {
            'fields': ('company_name', 'inn', 'ogrn', 'contact_email', 'contact_phone')
        }),
        (_('Обработка заявки'), {
            'fields': ('processed_by', 'processed_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        (_('Даты'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # Действия для администраторов
    actions = ['approve_selected', 'reject_selected']

    def get_processed_by(self, obj):
        if obj.processed_by:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/auth/user/{obj.processed_by.id}/change/",
                               obj.processed_by.username)
        return "-"
    get_processed_by.short_description = _("Обработана")

    def approve_selected(self, request, queryset):
        """Массовое одобрение выбранных заявок"""
        updated_count = 0
        for application in queryset.filter(status='pending'):
            if application.status == 'pending':
                try:
                    # Используем сервис для одобрения
                    approve_partner_application(application, request.user)
                    updated_count += 1
                except Exception as e:
                    # Если возникла ошибка, пропускаем эту заявку
                    continue

        self.message_user(
            request,
            f"Одобрено заявок: {updated_count}",
            level='SUCCESS' if updated_count > 0 else 'WARNING'
        )
    approve_selected.short_description = _("Одобрить выбранные заявки")

    def reject_selected(self, request, queryset):
        """Массовое отклонение выбранных заявок"""
        updated_count = 0
        for application in queryset.filter(status='pending'):
            if application.status == 'pending':
                try:
                    # Используем сервис для отклонения
                    reject_partner_application(application, request.user, "Массовое отклонение")
                    updated_count += 1
                except Exception as e:
                    # Если возникла ошибка, пропускаем эту заявку
                    continue

        self.message_user(
            request,
            f"Отклонено заявок: {updated_count}",
            level='SUCCESS' if updated_count > 0 else 'WARNING'
        )
    reject_selected.short_description = _("Отклонить выбранных заявок")


@admin.register(Partner, site=admin_site)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'inn', 'owner_display', 'validated', 'created_at']
    list_filter = ['validated', ('created_at', admin.DateFieldListFilter), 'owner']
    search_fields = ['name', 'inn', 'ogrn', 'email', 'owner__username', 'owner__email']
    list_select_related = ['owner']

    # Поля в режиме редактирования
    fieldsets = [
        (None, {
            'fields': ['name', 'owner']
        }),
        (_('Контактная информация'), {
            'fields': ['email', 'phone', 'address']
        }),
        (_('Юридические реквизиты'), {
            'fields': ['legal_form', 'inn', 'ogrn', 'kpp']
        }),
        (_('Валидация'), {
            'fields': ['validated', 'validated_at'],
            'classes': ['collapse']
        }),
        (_('Даты'), {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Только для чтения поля
    readonly_fields = ['created_at', 'updated_at', 'validated_at']

    # Действия в админке
    actions = ['mark_as_validated', 'mark_as_not_validated']

    def owner_display(self, obj):
        """Отображение владельца с ссылкой на профиль"""
        if obj.owner:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/auth/user/{obj.owner.id}/change/",
                               obj.owner.username)
        return "-"
    owner_display.short_description = _("Владелец")
    owner_display.admin_order_field = 'owner__username'

    def mark_as_validated(self, request, queryset):
        updated = queryset.update(validated=True)
        self.message_user(request, f"Помечено как проверено: {updated} партнеров")
    mark_as_validated.short_description = _("Пометить как проверенные")

    def mark_as_not_validated(self, request, queryset):
        updated = queryset.update(validated=False)
        self.message_user(request, f"Помечено как непроверено: {updated} партнеров")
    mark_as_not_validated.short_description = _("Пометить как непроверенные")

@admin.register(PartnerMember, site=admin_site)
class PartnerMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'partner_link', 'user_link', 'role_display', 'pickup_point_link', 'is_active', 'created_at']
    list_filter = [
        ('partner', admin.RelatedOnlyFieldListFilter),
        'role',
        'is_active',
        'can_manage_members',
        'can_view_finance',
        ('pickup_point', admin.RelatedOnlyFieldListFilter),
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = [
        'name',
        'work_email',
        'work_phone',
        'employee_id',
        'partner__name',
        'user__username',
        'user__email'
    ]
    list_select_related = ['partner', 'user']

    # Автодополнение для полей ForeignKey
    autocomplete_fields = ['partner', 'user']

    # Поля в режиме редактирования
    fieldsets = [
        (None, {
            'fields': ['partner', 'user', 'name']
        }),
        (_('Контактная информация'), {
            'fields': ['work_email', 'work_phone', 'employee_id']
        }),
        (_('Роли и права'), {
            'fields': ['role', 'can_manage_members', 'can_view_finance', 'is_active']
        }),
        (_('Привязка к пункту выдачи'), {
            'fields': ['pickup_point'],
            'classes': ['collapse']
        }),
        (_('Даты'), {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Только для чтения поля
    readonly_fields = ['created_at', 'updated_at']

    def partner_link(self, obj):
        """Ссылка на партнера"""
        if obj.partner:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/partners/partner/{obj.partner.id}/change/",
                               obj.partner.name)
        return "-"
    partner_link.short_description = _("Партнер")
    partner_link.admin_order_field = 'partner__name'

    def user_link(self, obj):
        """Ссылка на пользователя"""
        if obj.user:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/auth/user/{obj.user.id}/change/",
                               obj.user.username)
        return "-"
    user_link.short_description = _("Пользователь")
    user_link.admin_order_field = 'user__username'

    # Метод для отображения роли в списке
    def role_display(self, obj):
        return obj.get_role_display()
    role_display.short_description = _("Роль")
    role_display.admin_order_field = 'role'

    def pickup_point_link(self, obj):
        """Ссылка на пункт выдачи"""
        if obj.pickup_point:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/partners/pickuppoint/{obj.pickup_point.id}/change/",
                               obj.pickup_point.name)
        return "-"
    pickup_point_link.short_description = _("Пункт выдачи")
    pickup_point_link.admin_order_field = 'pickup_point__name'

    # Действия в админке
    actions = ['activate_members', 'deactivate_members', 'grant_management_rights', 'revoke_management_rights']

    def activate_members(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано: {updated} членов партнера")
    activate_members.short_description = _("Активировать выбранных")

    def deactivate_members(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано: {updated} членов партнера")
    deactivate_members.short_description = _("Деактивировать выбранных")

    def grant_management_rights(self, request, queryset):
        updated = queryset.update(can_manage_members=True)
        self.message_user(request, f"Предоставлены права управления: {updated} членам")
    grant_management_rights.short_description = _("Предоставить права управления")

    def revoke_management_rights(self, request, queryset):
        updated = queryset.update(can_manage_members=False)
        self.message_user(request, f"Отозваны права управления: {updated} членам")
    revoke_management_rights.short_description = _("Отозвать права управления")


@admin.register(PickupPoint, site=admin_site)
class PickupPointAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'partner_link', 'address', 'is_active', 'created_at']
    list_filter = [
        ('partner', admin.RelatedOnlyFieldListFilter),
        'is_active',
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = [
        'name',
        'address',
        'location_details',
        'work_schedule',
        'partner__name',
        'partner__inn'
    ]
    list_select_related = ['partner']

    # Автодополнение для поля партнера
    autocomplete_fields = ['partner']

    # Поля в режиме редактирования
    fieldsets = [
        (None, {
            'fields': ['partner', 'name']
        }),
        (_('Адрес и расположение'), {
            'fields': ['address', 'location_details']
        }),
        (_('Операционная информация'), {
            'fields': ['work_schedule', 'phone', 'email']
        }),
        (_('Статус'), {
            'fields': ['is_active']
        }),
        (_('Даты'), {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    # Только для чтения поля
    readonly_fields = ['created_at', 'updated_at']

    def partner_link(self, obj):
        """Ссылка на партнера"""
        if obj.partner:
            return format_html('<a href="{}">{}</a>',
                               f"/admin/partners/partner/{obj.partner.id}/change/",
                               obj.partner.name)
        return "-"
    partner_link.short_description = _("Партнер")
    partner_link.admin_order_field = 'partner__name'

    # Действия в админке
    actions = ['activate_pickup_points', 'deactivate_pickup_points']

    def activate_pickup_points(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Активировано: {updated} пунктов выдачи")
    activate_pickup_points.short_description = _("Активировать выбранные")

    def deactivate_pickup_points(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Деактивировано: {updated} пунктов выдачи")
    deactivate_pickup_points.short_description = _("Деактивировать выбранные")