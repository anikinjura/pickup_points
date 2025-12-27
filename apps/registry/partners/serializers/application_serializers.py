# apps/registry/partners/serializers/application_serializers.py
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from apps.registry.partners.models.partner_application import PartnerApplication
from apps.registry.partners.models.partner import Partner
from apps.registry.partners.models.partner_member import PartnerMember
from apps.registry.partners.validators.field_validators import validate_inn, validate_ogrn
from apps.registry.partners.serializers.validation_mixins import (
    PartnerApplicationValidationMixin,
    validate_protected_fields
)

User = get_user_model()

class PartnerApplicationCreateSerializer(PartnerApplicationValidationMixin, serializers.ModelSerializer):
    """Сериализатор для создания заявки."""

    class Meta:
        model = PartnerApplication
        fields = ['company_name', 'inn', 'ogrn', 'contact_email', 'contact_phone']
        extra_kwargs = {
            'company_name': {'required': True},
            'inn': {'required': True},
            'ogrn': {'required': True},
            'contact_email': {'required': True},
            'contact_phone': {'required': True},
        }

    def validate(self, attrs):
        """Полная валидация при создании заявки."""
        attrs = self.full_partner_application_validation(attrs)
        return attrs


class PartnerApplicationUserUpdateSerializer(PartnerApplicationValidationMixin, serializers.ModelSerializer):
    """Сериализатор для обновления заявки пользователем - только основные поля."""

    class Meta:
        model = PartnerApplication
        fields = ['company_name', 'inn', 'ogrn', 'contact_email', 'contact_phone', 'status']
        read_only_fields = ['status']  # status нельзя изменить пользователю

    def validate(self, attrs):
        """Валидация при обновлении заявки пользователем."""
        request = self.context.get('request')
        user = request.user if request else None

        # Проверяем, что обычный пользователь не пытается изменить защищённые поля
        attrs = validate_protected_fields(attrs, user)

        # Если кто-то пытается изменить status, даже если он в read_only, всё равно проверяем
        if user and not user.is_staff:
            if 'status' in attrs:
                raise serializers.ValidationError({'status': 'Недостаточно прав для изменения статуса'})

        # Валидация данных заявки (общая логика)
        attrs = self.full_partner_application_validation(attrs)
        return attrs


class PartnerApplicationAdminSerializer(serializers.ModelSerializer):
    """Сериализатор для администратора - полный доступ с защитой через бизнес-логику."""

    class Meta:
        model = PartnerApplication
        fields = '__all__'


class PartnerApplicationSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра заявки."""

    class Meta:
        model = PartnerApplication
        fields = '__all__'


class UserStatusSerializer(serializers.Serializer):
    """Сериализатор для статуса пользователя."""
    has_partners = serializers.BooleanField()
    has_memberships = serializers.BooleanField()
    has_memberships_active = serializers.BooleanField(required=False, default=False)  # Новое поле
    has_pending_application = serializers.BooleanField()
    message = serializers.CharField()
    partners = serializers.ListField(child=serializers.DictField(), required=False)