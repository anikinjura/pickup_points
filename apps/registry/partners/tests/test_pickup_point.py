# apps/registry/partners/tests/test_pickup_point.py
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.registry.partners.models import Partner, PickupPoint


class PickupPointModelTest(TestCase):
    """Тесты для модели PickupPoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.partner = Partner.objects.create(
            name='Test Partner',
            owner=self.user,
            inn='123456789012',
            ogrn='1234567890123'
        )

    def test_create_pickup_point(self):
        """Тест создания ПВЗ"""
        pickup_point = PickupPoint.objects.create(
            name='Test Pickup Point',
            partner=self.partner,
            address='Test Address',
            work_schedule='с 9:00 до 21:00'
        )
        self.assertEqual(pickup_point.name, 'Test Pickup Point')
        self.assertEqual(pickup_point.partner, self.partner)

    def test_pickup_point_str_representation(self):
        """Тест строкового представления ПВЗ"""
        pickup_point = PickupPoint.objects.create(
            name='Test Pickup Point',
            partner=self.partner,
            address='Test Address',
            work_schedule='с 9:00 до 21:00'
        )
        expected_str = f"Test Pickup Point ({self.partner.name})"
        self.assertEqual(str(pickup_point), expected_str)

    def test_pickup_point_unique_name_per_partner_validation(self):
        """Тест валидации уникальности наименования ПВЗ в рамках партнера"""
        # Создаем первый ПВЗ
        PickupPoint.objects.create(
            name='Same Name',
            partner=self.partner,
            address='Test Address 1',
            work_schedule='с 9:00 до 21:00'
        )

        # Создаем второй с тем же именем для того же партнера - должна быть ошибка валидации
        pickup_point = PickupPoint(
            name='Same Name',
            partner=self.partner,
            address='Test Address 2',
            work_schedule='с 9:00 до 21:00'
        )

        with self.assertRaises(Exception) as context:
            pickup_point.full_clean()  # Вызываем валидацию

        self.assertIn('name', str(context.exception))


class PickupPointAPITest(TestCase):
    """Тесты для API ПВЗ"""

    def setUp(self):
        self.client = APIClient()
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
        self.partner = Partner.objects.create(
            name='Test Partner',
            owner=self.user,
            inn='123456789012',
            ogrn='1234567890123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_pickup_point(self):
        """Тест создания ПВЗ через API"""
        # Сначала пометим партнера как проверенного
        self.partner.validated = True
        self.partner.save()

        data = {
            'name': 'New Pickup Point',
            'partner': self.partner.id,
            'address': 'New Address',
            'work_schedule': 'с 8:00 до 20:00'
        }
        response = self.client.post(reverse('pickup-point-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PickupPoint.objects.count(), 1)

    def test_create_pickup_point_for_unvalidated_partner(self):
        """Тест создания ПВЗ для партнера, который не прошёл проверку"""
        # Убедимся, что партнер не проверен
        self.partner.validated = False
        self.partner.save()

        data = {
            'name': 'New Pickup Point',
            'partner': self.partner.id,
            'address': 'New Address',
            'work_schedule': 'с 8:00 до 20:00'
        }
        response = self.client.post(reverse('pickup-point-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PickupPoint.objects.count(), 0)
        self.assertIn('partner', response.data)

    def test_list_pickup_points(self):
        """Тест получения списка ПВЗ"""
        PickupPoint.objects.create(
            name='Test Pickup Point',
            partner=self.partner,
            address='Test Address',
            work_schedule='с 9:00 до 21:00'
        )
        response = self.client.get(reverse('pickup-point-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_update_pickup_point(self):
        """Тест обновления ПВЗ"""
        # Сначала пометим партнера как проверенного
        self.partner.validated = True
        self.partner.save()

        pickup_point = PickupPoint.objects.create(
            name='Old Name',
            partner=self.partner,
            address='Test Address',
            work_schedule='с 9:00 до 21:00'
        )
        data = {
            'name': 'Updated Name',
            'partner': self.partner.id,
            'address': 'Updated Address',
            'work_schedule': 'с 10:00 до 22:00'
        }
        response = self.client.put(
            reverse('pickup-point-detail', kwargs={'pk': pickup_point.id}),
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pickup_point.refresh_from_db()
        self.assertEqual(pickup_point.name, 'Updated Name')

    def test_delete_pickup_point(self):
        """Тест удаления ПВЗ"""
        pickup_point = PickupPoint.objects.create(
            name='To Delete',
            partner=self.partner,
            address='Test Address',
            work_schedule='с 9:00 до 21:00'
        )
        response = self.client.delete(
            reverse('pickup-point-detail', kwargs={'pk': pickup_point.id})
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PickupPoint.objects.count(), 0)

    def test_address_search_functionality(self):
        """Тест функциональности поиска по адресу."""
        # Сначала пометим партнера как проверенного
        self.partner.validated = True
        self.partner.save()

        # Создаем несколько ПВЗ с разными адресами для тестирования поиска
        PickupPoint.objects.create(
            name='ПВЗ Центральный',
            partner=self.partner,
            address='г. Москва, ул. Тверская, д. 1',
            work_schedule='с 9:00 до 21:00',
            is_active=True
        )

        PickupPoint.objects.create(
            name='ПВЗ Северный',
            partner=self.partner,
            address='г. Москва, ул. Ленинградское шоссе, д. 25',
            work_schedule='с 10:00 до 20:00',
            is_active=True
        )

        PickupPoint.objects.create(
            name='ПВЗ Южный',
            partner=self.partner,
            address='г. Санкт-Петербург, ул. Невский, д. 10',
            work_schedule='с 8:00 до 22:00',
            is_active=True
        )

        # Тестируем общий поиск по слову "Москва"
        response = self.client.get(reverse('pickup-point-list') + '?search=Москва')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        moscow_count = len([pp for pp in results if 'Москва' in pp['address']])
        self.assertGreaterEqual(moscow_count, 2)  # Должно быть как минимум 2 ПВЗ в Москве

        # Тестируем фильтрацию по частичному адресу
        response = self.client.get(reverse('pickup-point-list') + '?address=Тверская')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        tverskaya_count = len([pp for pp in results if 'Тверская' in pp['address']])
        self.assertEqual(tverskaya_count, 1)  # Должен быть 1 ПВЗ с Тверской

        # Тестируем фильтрацию по городу
        response = self.client.get(reverse('pickup-point-list') + '?address__icontains=Санкт')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        spb_count = len([pp for pp in results if 'Санкт' in pp['address']])
        self.assertEqual(spb_count, 1)  # Должен быть 1 ПВЗ в СПб

        # Тестируем точный поиск по адресу
        response = self.client.get(reverse('pickup-point-list') + '?address_exact=г. Москва, ул. Тверская, д. 1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        exact_count = len([pp for pp in results if pp['address'] == 'г. Москва, ул. Тверская, д. 1'])
        self.assertEqual(exact_count, 1)  # Должен быть 1 ПВЗ с точным адресом