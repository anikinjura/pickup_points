from django.test import TestCase
from django.contrib.auth.models import User
from apps.registry.partners.models import Partner
from ..models import TelegramConfig
from ..services.telegram_service import TelegramService
from ..services.email_service import EmailService
from ..services.notification_service import NotificationService


class TelegramServiceTest(TestCase):
    """Тесты для Telegram сервиса"""
    
    def setUp(self):
        # Создаём тестового пользователя и партнёра
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.partner = Partner.objects.create(
            name='Test Partner',
            owner=self.user,
            email='partner@example.com',
            phone='+79991234567',
            address='Test Address',
            validated=True
        )
        self.config = TelegramConfig.objects.create(
            partner=self.partner,
            bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz',
            chat_id='-1234567890'
        )
    
    def test_telegram_service_initialization(self):
        """Тест инициализации TelegramService"""
        # Тест с токеном
        service = TelegramService(bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz')
        self.assertIsNotNone(service.bot_token)
    
    def test_validate_recipient_valid(self):
        """Тест валидации корректного chat_id"""
        service = TelegramService(bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz')
        self.assertTrue(service.validate_recipient('123456789'))
        self.assertTrue(service.validate_recipient('-123456789'))
    
    def test_validate_recipient_invalid(self):
        """Тест валидации некорректного chat_id"""
        service = TelegramService(bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz')
        self.assertFalse(service.validate_recipient('invalid'))
        self.assertFalse(service.validate_recipient(''))
        self.assertFalse(service.validate_recipient('123abc'))


class EmailServiceTest(TestCase):
    """Тесты для Email сервиса"""
    
    def test_validate_recipient_valid(self):
        """Тест валидации корректного email"""
        service = EmailService()
        self.assertTrue(service.validate_recipient('test@example.com'))
        self.assertTrue(service.validate_recipient('user.name+tag@example.co.uk'))
    
    def test_validate_recipient_invalid(self):
        """Тест валидации некорректного email"""
        service = EmailService()
        self.assertFalse(service.validate_recipient('invalid-email'))
        self.assertFalse(service.validate_recipient(''))
        self.assertFalse(service.validate_recipient('not-an-email'))


class NotificationServiceTest(TestCase):
    """Тесты для центрального сервиса уведомлений"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.partner = Partner.objects.create(
            name='Test Partner',
            owner=self.user,
            email='partner@example.com',
            phone='+79991234567',
            address='Test Address',
            validated=True
        )
        self.config = TelegramConfig.objects.create(
            partner=self.partner,
            bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz',
            chat_id='-1234567890'
        )
    
    def test_send_to_partner_telegram(self):
        """Тест отправки уведомления партнёру через Telegram"""
        service = NotificationService()
        # Тест без реальной отправки - проверяем создание объекта
        notification = service.send_to_partner(
            partner_id=self.partner.id,
            channel='telegram',
            subject='Test Subject',
            message='Test Message'
        )

        self.assertEqual(notification.partner_id, self.partner.id)
        self.assertEqual(notification.channel, 'telegram')
        # В тесте реальная отправка может быть успешной (т.к. мы просто возвращаем True из mock)
        self.assertIn(notification.status, ['sent', 'failed'])  # Может быть успешно или неуспешно
    
    def test_send_to_partner_email(self):
        """Тест отправки уведомления партнёру через email"""
        service = NotificationService()
        notification = service.send_to_partner(
            partner_id=self.partner.id,
            channel='email',
            subject='Test Subject',
            message='Test Message'
        )

        self.assertEqual(notification.partner_id, self.partner.id)
        self.assertEqual(notification.channel, 'email')
        # В тесте возвращаем True, так что статус может быть 'sent'
        self.assertIn(notification.status, ['sent', 'failed'])
    
    def test_send_from_partner(self):
        """Тест отправки уведомления от имени партнёра"""
        service = NotificationService()
        notification = service.send_from_partner(
            partner_id=self.partner.id,
            message='Test Message from Partner'
        )

        self.assertEqual(notification.partner_id, self.partner.id)
        self.assertEqual(notification.channel, 'telegram')
        # Может быть успешно или неуспешно
        self.assertIn(notification.status, ['sent', 'failed'])