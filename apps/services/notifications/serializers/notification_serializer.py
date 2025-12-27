from rest_framework import serializers
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from ..models import Notification
from ..validation_mixins import NotificationChannelValidationMixin


class NotificationSerializer(serializers.ModelSerializer, NotificationChannelValidationMixin):
    """Сериализатор для уведомления (для чтения)"""

    class Meta:
        model = Notification
        fields = [
            'id', 'partner', 'channel', 'status', 'subject',
            'message', 'recipient', 'sent_at', 'error_message', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'sent_at', 'error_message', 'created_at']

    def to_representation(self, instance):
        """Добавляем partner_id в представление для Swagger"""
        data = super().to_representation(instance)
        # Добавляем partner_id если нужен для отображения
        if hasattr(instance, 'partner') and instance.partner:
            data['partner'] = instance.partner.id
        return data


class CreateNotificationSerializer(serializers.ModelSerializer, NotificationChannelValidationMixin):
    """Сериализатор для создания уведомления (без partner)"""

    class Meta:
        model = Notification
        fields = [
            'channel', 'subject', 'message', 'recipient'
        ]