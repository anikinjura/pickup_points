from celery import shared_task
from django.utils import timezone
from ..services.notification_service import NotificationService
from ..models import TelegramConfig


@shared_task
def send_notification_task(partner_id: int, channel: str, subject: str, message: str, 
                          context: dict = None):
    """Асинхронная задача отправки уведомления"""
    service = NotificationService()
    return service.send_to_partner(partner_id, channel, subject, message, context)


@shared_task
def send_notification_from_partner_task(partner_id: int, message: str, context: dict = None):
    """Асинхронная задача отправки уведомления от имени партнёра"""
    service = NotificationService()
    return service.send_from_partner(partner_id, message, context)


@shared_task
def validate_telegram_config_task(config_id: int):
    """Асинхронная задача валидации telegram конфигурации"""
    try:
        config = TelegramConfig.objects.get(id=config_id)

        # Используем прямой вызов к Telegram API для валидации
        import requests

        # Проверяем токен через getMe
        bot_token = config.bot_token
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url)
        response.raise_for_status()

        result = response.json()
        if not result.get('ok', False):
            config.is_active = False
            config.save()
            return False

        # Пытаемся отправить тестовое сообщение
        send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        send_data = {
            'chat_id': config.chat_id,
            'text': 'Тестовое сообщение для валидации',
            'parse_mode': 'HTML'
        }

        send_response = requests.post(send_url, data=send_data)
        send_response.raise_for_status()

        send_result = send_response.json()
        if send_result.get('ok', False):
            config.validated_at = timezone.now()
            config.is_active = True
            config.save()
            return True
        else:
            config.is_active = False
            config.save()
            return False

    except Exception as e:
        config.is_active = False
        config.save()
        return False