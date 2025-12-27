from django.conf import settings
from django.core.exceptions import ValidationError
from .base_notification import BaseNotificationService


class TelegramService(BaseNotificationService):
    """Сервис для отправки уведомлений через Telegram"""

    def __init__(self, bot_token: str = None):
        """Если токен не передан, используется глобальный токен"""
        token = bot_token or getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            raise ValueError("Необходим токен для инициализации TelegramService")
        self.bot_token = token
    
    def send(self, recipient: str, subject: str, message: str, context: dict = None) -> bool:
        """Отправка сообщения в Telegram"""
        try:
            # Применяем контекст к сообщению если есть
            if context:
                try:
                    message = message.format(**context)
                    if subject:
                        subject = subject.format(**context)
                except KeyError:
                    # Если в контексте нет нужных ключей, отправляем без форматирования
                    pass

            full_message = f"{subject}\n\n{message}" if subject else message

            # Используем прямой вызов к Telegram API для синхронной отправки
            import requests

            # Используем сохранённый токен
            bot_token = self.bot_token
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = {
                'chat_id': recipient,
                'text': full_message,
                'parse_mode': 'HTML'  # или 'Markdown', если нужно форматирование
            }

            response = requests.post(url, data=data)
            response.raise_for_status()  # Вызывает исключение если статус не 200

            result = response.json()
            return result.get('ok', False)

        except Exception as e:
            # Логируем ошибку (в реальном приложении использовать logging)
            print(f"Ошибка отправки в Telegram: {str(e)}")
            return False
    
    def validate_recipient(self, recipient: str) -> bool:
        """Валидация Telegram chat_id"""
        if not recipient:
            return False
        try:
            # Telegram chat_id может быть отрицательным (для групп)
            chat_id = str(recipient).lstrip('-')
            return chat_id.isdigit() and len(chat_id) > 0
        except:
            return False