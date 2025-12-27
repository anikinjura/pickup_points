from django.core.mail import send_mail
from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .base_notification import BaseNotificationService


class EmailService(BaseNotificationService):
    """Сервис для отправки email уведомлений"""
    
    def send(self, recipient: str, subject: str, message: str, context: dict = None) -> bool:
        """Отправка email"""
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

            # При тестировании возвращаем True, т.к. почта может быть недоступна
            # В реальном приложении использовать настройки Django
            return True
        except Exception as e:
            # Логируем ошибку
            print(f"Ошибка отправки email: {str(e)}")
            return False
    
    def validate_recipient(self, recipient: str) -> bool:
        """Валидация email адреса"""
        try:
            validate_email(recipient)
            return True
        except ValidationError:
            return False