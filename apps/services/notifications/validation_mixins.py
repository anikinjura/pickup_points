from rest_framework import serializers


class NotificationChannelValidationMixin:
    """Миксин для валидации канала уведомления"""

    def validate_channel(self, value):
        """Валидация канала уведомления"""
        from .models import Notification  # Импорт внутри метода для избежания циклических зависимостей
        valid_channels = [choice[0] for choice in Notification.CHANNEL_CHOICES]
        if value not in valid_channels:
            raise serializers.ValidationError(f"Канал должен быть одним из: {valid_channels}")
        return value


class TelegramTokenValidationMixin:
    """Миксин для валидации Telegram токена"""

    def validate_bot_token(self, value):
        """Валидация формата токена"""
        parts = value.split(':')
        if len(parts) != 2 or not parts[0].isdigit():
            raise serializers.ValidationError("Неверный формат токена. Формат: DIGITS:ALPHANUMERIC")
        return value

    def validate_chat_id(self, value):
        """Валидация формата chat_id"""
        if not str(value).lstrip('-').isdigit():
            raise serializers.ValidationError("Неверный формат chat_id. Должен содержать только цифры (с возможным знаком -)")
        return value