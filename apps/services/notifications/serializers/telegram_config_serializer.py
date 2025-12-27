from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models import TelegramConfig
from ..validation_mixins import TelegramTokenValidationMixin


class PartnerTelegramConfigSerializer(serializers.ModelSerializer, TelegramTokenValidationMixin):
    """Сериализатор для настройки telegram конфигурации партнёром"""

    class Meta:
        model = TelegramConfig
        fields = [
            'bot_token', 'chat_id', 'is_active', 'is_default',
            'created_at', 'updated_at', 'validated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'validated_at']