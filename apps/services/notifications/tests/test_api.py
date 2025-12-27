from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch
from apps.registry.partners.models import Partner
from apps.services.notifications.models import TelegramConfig, Notification


class NotificationAPITest(TestCase):
    """Интеграционные тесты для API уведомлений"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True  # Для тестов даём права администратора
        )
        self.partner = Partner.objects.create(
            name='Test Partner',
            owner=self.user,
            email='partner@example.com',
            phone='+79991234567',
            address='Test Address',
            validated=True
        )
        self.client.force_authenticate(user=self.user)

    @patch('apps.services.notifications.tasks.notification_tasks.send_notification_from_partner_task.delay')
    def test_send_partner_notification(self, mock_task):
        """Тест отправки уведомления от имени партнёра"""
        # Мокаем задачу
        mock_task.return_value.id = 'test_task_id'

        # Предварительно создадим Telegram конфигурацию
        TelegramConfig.objects.create(
            partner=self.partner,
            bot_token='123456789:ABCdefGhIjKlMnOpQrStUvWxYz',
            chat_id='-1234567890',
            is_active=True
        )

        # Тест отправки уведомления от имени партнёра
        notification_data = {
            'message': 'Test notification from partner'
        }
        response = self.client.post(reverse('partner-send-partner-notification', kwargs={'pk': self.partner.id}), notification_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('task_id', response.data)
        # Проверяем, что задача была вызвана
        mock_task.assert_called_once()

    def test_partner_notifications_list(self):
        """Тест получения списка уведомлений партнёра"""
        # Создадим несколько уведомлений для партнёра
        Notification.objects.create(
            partner=self.partner,
            channel='telegram',
            status='sent',
            subject='Test Subject',
            message='Test Message',
            recipient='test@example.com'
        )

        response = self.client.get(reverse('partner-notifications', kwargs={'pk': self.partner.id}))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)

    def test_create_partner_notification(self):
        """Тест создания уведомления для партнёра"""
        notification_data = {
            'channel': 'email',
            'subject': 'Test Subject',
            'message': 'Test Message',
            'recipient': 'test@example.com'
        }

        response = self.client.post(
            reverse('partner-create-notification', kwargs={'pk': self.partner.id}),
            notification_data
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['partner'], self.partner.id)
        self.assertEqual(response.data['channel'], 'email')
        self.assertEqual(response.data['message'], 'Test Message')


class NotificationServiceIntegrationTest(TestCase):
    """Интеграционные тесты для сервиса уведомлений"""

    def setUp(self):
        self.client = APIClient()
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
        # Создадим уведомление для теста
        self.notification = Notification.objects.create(
            partner=self.partner,
            channel='email',
            status='pending',
            subject='Integration Test',
            message='Integration Test Message',
            recipient='test@example.com'
        )
        # Предварительно создадим конфигурацию
        TelegramConfig.objects.create(
            partner=self.partner,
            bot_token='987654321:ZYXWVUTSRQPONMLKJIHGFEDCBA',
            chat_id='-9876543210',
            is_active=True
        )
        self.client.force_authenticate(user=self.user)

    def test_partner_notifications_workflow(self):
        """Тест полного цикла работы с уведомлениями партнёра"""
        # 1. Создание уведомления
        notification_data = {
            'channel': 'telegram',
            'subject': 'Workflow Test',
            'message': 'Workflow Test Message',
            'recipient': '-1234567890'
        }
        response = self.client.post(
            reverse('partner-create-notification', kwargs={'pk': self.partner.id}),
            notification_data
        )
        self.assertEqual(response.status_code, 201)

        # 2. Получение списка уведомлений
        response = self.client.get(reverse('partner-notifications', kwargs={'pk': self.partner.id}))
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.data), 0)

    def test_get_partner_telegram_config(self):
        """Тест получения Telegram конфигурации партнёра"""
        # Сначала создадим конфигурацию через API
        config_data = {
            'bot_token': '543210987:TESTINGABCDEF123456',
            'chat_id': '-5555555555',
            'is_active': True,
            'is_default': False
        }

        # Используем set_telegram_config для создания конфигурации
        response = self.client.post(
            reverse('partner-set-telegram-config', kwargs={'pk': self.partner.id}),
            config_data
        )
        self.assertEqual(response.status_code, 200)

        # Теперь получим конфигурацию
        response = self.client.get(reverse('partner-get-telegram-config', kwargs={'pk': self.partner.id}))
        self.assertEqual(response.status_code, 200)
        # Должны получить данные конфигурации
        self.assertIsNotNone(response.data.get('chat_id'), f"chat_id отсутствует в ответе: {response.data}")
        self.assertEqual(response.data.get('chat_id'), '-5555555555')
        self.assertEqual(response.data.get('is_active'), True)
        self.assertEqual(response.data.get('bot_token'), '543210987:TESTINGABCDEF123456')
        self.assertEqual(response.data.get('is_default'), False)

    def test_set_partner_telegram_config(self):
        """Тест установки Telegram конфигурации партнёра"""
        config_data = {
            'bot_token': '111111111:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
            'chat_id': '-1111111111',
            'is_active': False,
            'is_default': True
        }

        response = self.client.post(
            reverse('partner-set-telegram-config', kwargs={'pk': self.partner.id}),
            config_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['bot_token'], config_data['bot_token'])
        self.assertEqual(response.data['chat_id'], config_data['chat_id'])
        self.assertEqual(response.data['is_active'], config_data['is_active'])
        self.assertEqual(response.data['is_default'], config_data['is_default'])

        # Проверим, что конфигурация действительно обновилась
        from apps.services.notifications.models import TelegramConfig
        config = TelegramConfig.objects.get(partner=self.partner)
        self.assertEqual(config.bot_token, config_data['bot_token'])
        self.assertEqual(config.chat_id, config_data['chat_id'])
        self.assertEqual(config.is_active, config_data['is_active'])

    @patch('apps.services.notifications.tasks.notification_tasks.validate_telegram_config_task.delay')
    def test_validate_partner_telegram_config(self, mock_task):
        """Тест валидации Telegram конфигурации партнёра"""
        # Мокаем задачу
        mock_task.return_value.id = 'test_validate_task_id'

        # Конфигурация уже создана в setUp
        response = self.client.post(reverse('partner-validate-telegram-config', kwargs={'pk': self.partner.id}))
        self.assertEqual(response.status_code, 200)
        self.assertIn('task_id', response.data)
        # Проверим, что задача была вызвана с правильным ID конфигурации
        mock_task.assert_called_once()