from rest_framework import serializers
from apps.services.notifications.models import Notification
from apps.services.notifications.validation_mixins import NotificationChannelValidationMixin


class CreateNotificationSerializer(serializers.ModelSerializer, NotificationChannelValidationMixin):
    """Сериализатор для создания уведомления (без partner)"""

    class Meta:
        model = Notification
        fields = [
            'channel', 'subject', 'message', 'recipient'
        ]


class SendPartnerNotificationSerializer(serializers.Serializer):
    """Сериализатор для отправки уведомления от имени партнёра"""

    message = serializers.CharField(
        help_text="Сообщение для отправки",
        required=True
    )