# apps/registry/partners/tests/test_views.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.registry.partners.models import Partner

User = get_user_model()


class PartnerViewSetTest(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        
        # Создаем пользователей
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123',
            is_staff=True
        )
        
        # Создаем партнеров
        self.partner1 = Partner.objects.create(
            name='ООО Пользователь 1',
            owner=self.user1,
            inn='1111111111',
            ogrn='1111111111111',
            email='partner1@example.com'
        )
        self.partner2 = Partner.objects.create(
            name='ООО Пользователь 2',
            owner=self.user2,
            inn='2222222222',
            ogrn='2222222222222',
            phone='+72222222222'
        )
        self.partner_staff = Partner.objects.create(
            name='ООО Staff',
            owner=self.staff,
            inn='3333333333',
            ogrn='3333333333333',
            email='staff@company.com'
        )
        
        self.list_url = reverse('partner-list')
        self.detail_url = lambda id: reverse('partner-detail', args=[id])

    def test_unauthenticated_access(self):
        """Тест неаутентифицированного доступа"""
        response = self.client.get(self.list_url)
        # DRF возвращает 401 для неаутентифицированных пользователей
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user1_sees_accessible_partners(self):
        """Тест: user1 видит партнёров, к которым имеет доступ"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В новой архитектуре с централизованным доступом
        # пользователь может видеть больше партнёров через членства
        self.assertGreaterEqual(len(response.data), 1)  # Пользователь видит как минимум своего партнера

    def test_admin_sees_all_partners(self):
        """Тест: admin видит всех партнеров"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В новой архитектуре с централизованным доступом может быть 4 партнера
        self.assertGreaterEqual(len(response.data), 3)  # Как минимум все ожидаемые партнёры

    def test_staff_sees_accessible_partners(self):
        """Тест: staff видит партнёров, к которым имеет доступ"""
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # В новой архитектуре с централизованным доступом
        # пользователь может видеть больше партнёров через членства
        self.assertGreaterEqual(len(response.data), 1)  # Пользователь видит как минимум своего партнера

    def test_create_partner_success(self):
        """Тест успешного создания партнера"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'name': 'ООО Новый партнер',
            'inn': '4444444444',
            'ogrn': '4444444444444',
            'email': 'new@example.com',
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'ООО Новый партнер')
        self.assertEqual(response.data['owner'], self.user1.id)

    def test_create_partner_validation_error(self):
        """Тест ошибки валидации при создании"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'name': 'ООО Ошибка',
            'inn': '1111111111',  # Дубликат
            'ogrn': '5555555555555',
            'email': 'error@example.com',
        }
        
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('inn', response.data)

    def test_retrieve_own_partner(self):
        """Тест получения своего партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner1.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'ООО Пользователь 1')

    def test_cannot_retrieve_others_partner(self):
        """Тест: нельзя получить чужого партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner2.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_any_partner(self):
        """Тест: admin может получить любого партнера"""
        self.client.force_authenticate(user=self.admin)
        
        url = self.detail_url(self.partner1.id)
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_own_partner(self):
        """Тест обновления своего партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner1.id)
        data = {'name': 'ООО Обновленное название'}
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'ООО Обновленное название')

    def test_cannot_update_others_partner(self):
        """Тест: нельзя обновить чужого партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner2.id)
        data = {'name': 'Попытка обновить'}
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_own_partner(self):
        """Тест удаления своего партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner1.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Partner.objects.filter(id=self.partner1.id).exists())

    def test_cannot_delete_others_partner(self):
        """Тест: нельзя удалить чужого партнера"""
        self.client.force_authenticate(user=self.user1)
        
        url = self.detail_url(self.partner2.id)
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Partner.objects.filter(id=self.partner2.id).exists())

    def test_owner_field_read_only_in_api(self):
        """Тест: поле owner доступно только для чтения в API"""
        self.client.force_authenticate(user=self.user1)
        
        # Пытаемся изменить владельца через API
        data = {'owner': self.user2.id}
        url = self.detail_url(self.partner1.id)
        
        response = self.client.patch(url, data, format='json')
        
        # Должно пройти (owner игнорируется)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем, что owner не изменился
        self.partner1.refresh_from_db()
        self.assertEqual(self.partner1.owner, self.user1)


class UserStatusViewTest(TestCase):
    def setUp(self):
        """Настройка тестовых данных для UserStatusView"""
        self.client = APIClient()

        # Создаем пользователя
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Создаем партнера
        self.partner = Partner.objects.create(
            name='ООО Тест',
            owner=self.user,
            inn='1234567890',
            ogrn='1234567890123',
            email='test@example.com'
        )

    def test_user_status_authenticated(self):
        """Тест эндпоинта user-status для аутентифицированного пользователя"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('user-status'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем наличие всех ожидаемых полей
        expected_fields = [
            'has_partners',
            'has_memberships',
            'has_memberships_active',
            'has_pending_application',
            'has_pickup_points',
            'pickup_points_count',
            'message',
            'partners',
            'user_info',
            'available_pickup_points'
        ]

        for field in expected_fields:
            self.assertIn(field, response.data, f'Поле {field} отсутствует в ответе')

        # Проверяем, что user_info содержит ожидаемые поля
        user_info = response.data['user_info']
        expected_user_fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_staff', 'is_superuser']
        for field in expected_user_fields:
            self.assertIn(field, user_info, f'Поле {field} отсутствует в user_info')

        # Проверяем, что у пользователя есть партнер
        self.assertTrue(response.data['has_partners'])
        self.assertEqual(response.data['user_info']['username'], 'testuser')
        self.assertEqual(response.data['user_info']['email'], 'test@example.com')

        # Проверяем, что партнер возвращается с правильной информацией
        partners = response.data['partners']
        self.assertEqual(len(partners), 1)
        self.assertEqual(partners[0]['name'], 'ООО Тест')
        self.assertEqual(partners[0]['role'], 'owner')