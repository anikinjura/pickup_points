from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseNotificationService(ABC):
    """Абстрактный класс для сервиса уведомлений"""
    
    @abstractmethod
    def send(self, recipient: str, subject: str, message: str, context: Dict[str, Any] = None) -> bool:
        """Отправка уведомления"""
        pass
    
    @abstractmethod
    def validate_recipient(self, recipient: str) -> bool:
        """Валидация получателя"""
        pass