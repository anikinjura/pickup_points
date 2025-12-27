from typing import Dict, Any
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .telegram_service import TelegramService
from .email_service import EmailService
from ..models import TelegramConfig, Notification


class NotificationService:
    """Централизованный сервис уведомлений"""

    def __init__(self):
        self.telegram_service = TelegramService
        self.email_service = EmailService()

    def send_to_partner(self, partner_id: int, channel: str, subject: str, message: str,
                       context: Dict[str, Any] = None) -> Notification:
        """Отправка уведомления партнёру"""
        # Создаём запись уведомления
        notification = Notification.objects.create(
            partner_id=partner_id,
            channel=channel,
            subject=subject,
            message=message,
            status='pending'
        )

        try:
            if channel == 'telegram':
                config = TelegramConfig.objects.get(partner_id=partner_id, is_active=True)
                service = TelegramService(bot_token=config.bot_token)
                recipient = config.chat_id
            elif channel == 'email':
                # Получаем email партнёра из модели
                from apps.registry.partners.models import Partner
                partner = Partner.objects.get(id=partner_id)
                recipient = partner.email
                service = self.email_service
            else:
                raise ValueError(f"Неподдерживаемый канал: {channel}")

            success = service.send(recipient, subject, message, context)

            notification.status = 'sent' if success else 'failed'
            notification.sent_at = timezone.now() if success else None
            if not success:
                notification.error_message = f"Ошибка отправки через {channel}"
            notification.save()

            return notification

        except TelegramConfig.DoesNotExist:
            notification.status = 'failed'
            notification.error_message = "Телеграм конфигурация не найдена"
            notification.save()
            return notification
        except Exception as e:
            notification.status = 'failed'
            notification.error_message = str(e)
            notification.save()
            return notification

    def send_from_partner(self, partner_id: int, message: str,
                         context: Dict[str, Any] = None) -> Notification:
        """Отправка уведомления от имени партнёра (только telegram)"""
        return self.send_to_partner(partner_id, 'telegram', '', message, context)