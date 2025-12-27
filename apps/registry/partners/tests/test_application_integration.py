"""
Интеграционные тесты для проверки API заявок на создание партнёров.

Тестирует интеграцию:
- ViewSet + Serializer + Service
- Права доступа
- Централизованная фильтрация
- API-взаимодействие
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from apps.registry.partners.models import PartnerApplication, Partner, PartnerMember

User = get_user_model()


class PartnerApplicationIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Создаём пользователей
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Создаём тестовую заявку
        self.application = PartnerApplication.objects.create(
            user=self.user,
            company_name='Тестовая Компания',
            inn='1111111111',
            ogrn='2222222222222',
            contact_email='test@example.com',
            contact_phone='+79999999999',
            status='pending'
        )
        
        # URL для API
        self.applications_list_url = reverse('application-list')
        self.application_detail_url = reverse('application-detail', args=[self.application.id])
        self.application_update_url = reverse('application-detail', args=[self.application.id])

    def test_user_can_create_application(self):
        """Тест: пользователь может создать заявку"""
        # Создаём другого пользователя, у которого нет активных заявок
        new_user = User.objects.create_user(
            username='newuser',
            email='new@example.com',
            password='newpass123'
        )
        self.client.force_authenticate(user=new_user)

        data = {
            'company_name': 'Новая Компания',
            'inn': '3333333333',
            'ogrn': '4444444444444',
            'contact_email': 'new@example.com',
            'contact_phone': '+78888888888'
        }

        response = self.client.post(self.applications_list_url, data, format='json')

        # Добавим отладочную информацию
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Ошибка создания заявки: {response.status_code}, детали: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Для этого кастомного API ожидаем специальный формат ответа
        self.assertEqual(response.data['status'], 'success')  # статус операции
        self.assertIn('application_id', response.data)
        self.assertIn('application_id', response.data)

    def test_user_cannot_approve_application(self):
        """Тест: обычный пользователь не может одобрить заявку"""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'status': 'approved'
        }
        
        response = self.client.patch(self.application_update_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_application(self):
        """Тест: администратор может одобрить заявку через API"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'status': 'approved'
        }
        
        response = self.client.patch(self.application_update_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], 'Заявка одобрена. Партнер создан.')
        
        # Проверяем, что заявка обновлена
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'approved')
        self.assertEqual(self.application.processed_by, self.admin_user)
        
        # Проверяем, что партнёр создан
        self.assertIsNotNone(self.application.partner)
        partner = self.application.partner
        self.assertEqual(partner.name, self.application.company_name)
        self.assertEqual(partner.owner, self.application.user)
        
        # Проверяем, что членство владельца создано
        owner_member = PartnerMember.objects.get(partner=partner, user=self.application.user)
        self.assertEqual(owner_member.role, 'director')

    def test_admin_can_reject_application(self):
        """Тест: администратор может отклонить заявку через API"""
        self.client.force_authenticate(user=self.admin_user)
        
        data = {
            'status': 'rejected',
            'rejection_reason': 'Тестовая причина отклонения'
        }
        
        response = self.client.patch(self.application_update_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['message'], 'Заявка отклонена.')
        self.assertEqual(response.data['reason'], 'Тестовая причина отклонения')
        
        # Проверяем, что заявка обновлена
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, 'rejected')
        self.assertEqual(self.application.processed_by, self.admin_user)
        self.assertEqual(self.application.rejection_reason, 'Тестовая причина отклонения')

    def test_admin_cannot_approve_approved_application(self):
        """Тест: администратор не может одобрить уже одобренную заявку"""
        # Сначала одобрим заявку
        self.client.force_authenticate(user=self.admin_user)
        approve_data = {'status': 'approved'}
        response = self.client.patch(self.application_update_url, approve_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Пытаемся одобрить снова
        response = self.client.patch(self.application_update_url, approve_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_cannot_reject_approved_application(self):
        """Тест: администратор не может отклонить уже одобренную заявку"""
        # Сначала одобрим заявку
        self.client.force_authenticate(user=self.admin_user)
        approve_data = {'status': 'approved'}
        response = self.client.patch(self.application_update_url, approve_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Пытаемся отклонить одобренную заявку
        reject_data = {'status': 'rejected', 'rejection_reason': 'Тест'}
        response = self.client.patch(self.application_update_url, reject_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_cannot_see_other_users_applications(self):
        """Тест: пользователь не видит чужие заявки"""
        # Создаём другую заявку от другого пользователя
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )

        other_application = PartnerApplication.objects.create(
            user=other_user,
            company_name='Чужая Компания',
            inn='5555555555',
            ogrn='6666666666666',
            contact_email='other@example.com',
            contact_phone='+77777777777',
            status='pending'
        )

        self.client.force_authenticate(user=self.user)

        # Запрашиваем список заявок
        response = self.client.get(self.applications_list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Проверяем, что пользователь НЕ видит чужую заявку
        # Он видит только свои заявки - в данном случае одну (из setUp)
        application_ids = [app['id'] for app in response.data['results']]
        self.assertNotIn(other_application.id, application_ids)
        # Пользователь всё ещё может видеть свои заявки (в данном случае - self.application)
        
        # Если бы у него была заявка, она бы появилась, но чужая - нет
        
    def test_admin_sees_all_applications(self):
        """Тест: администратор видит все заявки"""
        # Создаём другую заявку
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        
        PartnerApplication.objects.create(
            user=other_user,
            company_name='Другая Компания',
            inn='5555555555',
            ogrn='6666666666666',
            contact_email='other@example.com',
            contact_phone='+77777777777',
            status='pending'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Запрашиваем список заявок
        response = self.client.get(self.applications_list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Администратор должен видеть все заявки
        self.assertGreater(len(response.data['results']), 0)

    def test_application_status_validation_in_api(self):
        """Тест: валидация статуса в API"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Проверяем, что обычные пользователи не могут изменять статус
        self.client.force_authenticate(user=self.user)
        data = {'status': 'approved'}
        response = self.client.patch(self.application_update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_pending_application_cannot_be_updated(self):
        """Тест: заявки не в статусе pending не могут быть обновлены"""
        # Сначала отклоняем заявку
        self.client.force_authenticate(user=self.admin_user)
        reject_data = {'status': 'rejected', 'rejection_reason': 'Тест'}
        response = self.client.patch(self.application_update_url, reject_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Пытаемся одобрить отклонённую заявку
        approve_data = {'status': 'approved'}
        response = self.client.patch(self.application_update_url, approve_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)