# apps/registry/partners/serializers/validation_mixins.py
"""
Централизованные валидационные миксины для заявок на партнёра.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models.partner import Partner
from apps.registry.partners.models.partner_application import PartnerApplication
from apps.registry.partners.validators.field_validators import validate_inn, validate_ogrn


class PartnerApplicationValidationMixin:
    """Миксин для валидации данных заявки на партнёра."""
    
    def validate_inn_ogrn(self, attrs):
        """Валидация ИНН и ОГРН."""
        if 'inn' in attrs:
            validate_inn(attrs['inn'])
        if 'ogrn' in attrs:
            validate_ogrn(attrs['ogrn'])
        return attrs
    
    def validate_inn_uniqueness(self, attrs):
        """Проверка уникальности ИНН."""
        if 'inn' in attrs:
            # Проверка в существующих партнёрах
            if Partner.objects.filter(inn=attrs['inn']).exists():
                raise serializers.ValidationError({
                    'inn': _('Партнер с таким ИНН уже существует')
                })
            
            # Проверка в других заявках (если есть request)
            request = self.context.get('request')
            if request:
                user = request.user
                if user:
                    if PartnerApplication.objects.filter(inn=attrs['inn']).exclude(user=user).exists():
                        raise serializers.ValidationError({
                            'inn': _('Партнер с таким ИНН уже зарегистрирован в заявке')
                        })
        return attrs
    
    def full_partner_application_validation(self, attrs):
        """Полная валидация данных заявки."""
        attrs = self.validate_inn_ogrn(attrs)
        attrs = self.validate_inn_uniqueness(attrs)
        return attrs


def validate_protected_fields(attrs, user, allowed_fields=None):
    """
    Централизованный валидатор защищённых полей.
    
    Args:
        attrs: атрибуты для проверки
        user: пользователь, который пытается изменить
        allowed_fields: список разрешённых полей (если нужно ограничить)
    """
    if user and not user.is_staff:
        protected_fields = {'processed_by', 'processed_at', 'rejection_reason', 'partner', 'status'}
        if allowed_fields:
            protected_fields = protected_fields - set(allowed_fields)
        
        for field in protected_fields:
            if field in attrs:
                raise serializers.ValidationError({field: 'Недостаточно прав для изменения'})
    
    return attrs