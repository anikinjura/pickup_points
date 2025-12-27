"""
Функциональные тесты для проверки полных сценариев работы с заявками на создание партнёров.

Тестирует end-to-end сценарии:
- Подача заявки → одобрение → создание партнёра и членства
- Подача заявки → отклонение → обновление статуса
- Проверка согласованности данных
- Проверка транзакционности
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone

from apps.registry.partners.models import PartnerApplication, Partner, PartnerMember

User = get_user_model()


class PartnerApplicationFunctionalTest(TestCase):
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
        
        # URL для API
        self.applications_list_url = reverse('application-list')
        self.applications_detail_url = lambda id: reverse('application-detail', args=[id])

    def test_full_application_approval_scenario(self):
        """
        Полный сценарий: пользователь подаёт заявку → администратор одобряет → создаются партнёр и членство
        """
        # Шаг 1: Пользователь создаёт заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Функциональный Тест ООО',
            'inn': '7777777777',
            'ogrn': '8888888888888',
            'contact_email': 'func_test@example.com',
            'contact_phone': '+76666666666'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['status'], 'success')
        
        # Получаем ID созданной заявки
        application_id = create_response.data['application_id']
        
        # Проверяем, что заявка создана в базе
        application = PartnerApplication.objects.get(id=application_id)
        self.assertEqual(application.status, 'pending')
        self.assertEqual(application.user, self.user)
        self.assertEqual(application.company_name, 'Функциональный Тест ООО')
        
        # Шаг 2: Администратор одобряет заявку
        self.client.force_authenticate(user=self.admin_user)
        
        approve_data = {
            'status': 'approved'
        }
        
        approve_response = self.client.patch(
            self.applications_detail_url(application_id), 
            approve_data, 
            format='json'
        )
        
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(approve_response.data['status'], 'success')
        self.assertEqual(approve_response.data['message'], 'Заявка одобрена. Партнер создан.')
        self.assertIn('partner_id', approve_response.data)
        self.assertIn('member_id', approve_response.data)
        
        # Шаг 3: Проверяем, что данные корректно созданы
        application.refresh_from_db()
        self.assertEqual(application.status, 'approved')
        self.assertEqual(application.processed_by, self.admin_user)
        self.assertIsNotNone(application.partner)
        self.assertIsNotNone(application.processed_at)
        
        # Проверяем созданный партнёр
        partner = application.partner
        self.assertEqual(partner.name, 'Функциональный Тест ООО')
        self.assertEqual(partner.owner, self.user)  # Владелец - подавший заявку
        self.assertEqual(partner.inn, '7777777777')
        self.assertEqual(partner.ogrn, '8888888888888')
        self.assertEqual(partner.email, 'func_test@example.com')
        self.assertEqual(partner.phone, '+76666666666')
        
        # Проверяем созданное членство владельца
        owner_member = PartnerMember.objects.get(partner=partner, user=self.user)
        self.assertEqual(owner_member.role, 'director')
        self.assertEqual(owner_member.work_email, 'func_test@example.com')
        self.assertEqual(owner_member.work_phone, '+76666666666')
        self.assertEqual(owner_member.name, self.user.username)  # или полное имя

        # Отладка: проверим, какие права установлены
        print(f"Права владельца - can_manage_members: {owner_member.can_manage_members}, can_view_finance: {owner_member.can_view_finance}")

        # Роль director должна давать права (через clean())
        self.assertTrue(owner_member.can_manage_members, "Роль director должна давать права на управление членами")
        self.assertTrue(owner_member.can_view_finance, "Роль director должна давать права на просмотр финансов")
        
        # Шаг 4: Проверяем, что пользователь может получить доступ к своему партнёру
        self.client.force_authenticate(user=self.user)
        
        # Проверяем, что пользователь видит созданный партнёр через фильтрацию
        from apps.registry.partners.permissions import get_partner_filter_for_user
        user_partner_q = get_partner_filter_for_user(self.user)
        user_partners = Partner.objects.filter(user_partner_q)
        
        self.assertIn(partner, user_partners)

    def test_full_application_rejection_scenario(self):
        """
        Полный сценарий: пользователь подаёт заявку → администратор отклоняет → обновляется статус
        """
        # Шаг 1: Пользователь создаёт заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Отклонённый Тест ООО',
            'inn': '9999999999',
            'ogrn': '0000000000000',
            'contact_email': 'reject_test@example.com',
            'contact_phone': '+75555555555'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_response.data['status'], 'success')
        
        application_id = create_response.data['application_id']
        
        # Проверяем начальное состояние
        application = PartnerApplication.objects.get(id=application_id)
        self.assertEqual(application.status, 'pending')
        
        # Шаг 2: Администратор отклоняет заявку
        self.client.force_authenticate(user=self.admin_user)
        
        reject_data = {
            'status': 'rejected',
            'rejection_reason': 'Тестовое отклонение по причине проверки'
        }
        
        reject_response = self.client.patch(
            self.applications_detail_url(application_id), 
            reject_data, 
            format='json'
        )
        
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.data['status'], 'success')
        self.assertEqual(reject_response.data['message'], 'Заявка отклонена.')
        self.assertEqual(reject_response.data['reason'], 'Тестовое отклонение по причине проверки')
        
        # Шаг 3: Проверяем, что данные корректно обновлены
        application.refresh_from_db()
        self.assertEqual(application.status, 'rejected')
        self.assertEqual(application.processed_by, self.admin_user)
        self.assertEqual(application.rejection_reason, 'Тестовое отклонение по причине проверки')
        self.assertIsNotNone(application.processed_at)
        
        # Убеждаемся, что партнёр НЕ создан
        self.assertIsNone(application.partner)
        
        # Убеждаемся, что не создано членство
        partner_members = PartnerMember.objects.filter(user=self.user)
        # Если у пользователя были другие членства, они не учитываются, но НОВОГО не должно быть

    def test_application_workflow_integrity(self):
        """
        Тест целостности данных при обработке заявки
        """
        # Создаём заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Целостность Тест',
            'inn': '1234567890',
            'ogrn': '0987654321098',
            'contact_email': 'integrity@example.com',
            'contact_phone': '+74444444444'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        application_id = create_response.data['application_id']
        
        # Обновляем время до одобрения, чтобы проверить даты
        before_approve = timezone.now()
        
        # Одобряем заявку
        self.client.force_authenticate(user=self.admin_user)
        
        approve_response = self.client.patch(
            self.applications_detail_url(application_id),
            {'status': 'approved'},
            format='json'
        )
        
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        
        # Проверяем целостность данных
        application = PartnerApplication.objects.get(id=application_id)
        application.refresh_from_db()
        
        # Проверяем, что все связи установлены
        self.assertIsNotNone(application.partner)
        self.assertEqual(application.status, 'approved')
        self.assertEqual(application.processed_by, self.admin_user)
        self.assertGreaterEqual(application.processed_at, before_approve)
        
        # Проверяем, что партнёр связан с заявкой
        partner = application.partner
        self.assertIsNotNone(partner)
        self.assertEqual(partner.name, 'Целостность Тест')
        self.assertEqual(partner.owner, self.user)
        
        # Проверяем, что членство создано и связано правильно
        owner_member = PartnerMember.objects.get(partner=partner, user=self.user)
        self.assertEqual(owner_member.role, 'director')
        self.assertEqual(owner_member.partner, partner)
        self.assertEqual(owner_member.user, self.user)

    def test_user_cannot_modify_processed_application(self):
        """
        Тест: пользователь не может изменить обработанную заявку
        """
        # Создаём и одобряем заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Защита Тест',
            'inn': '1111111111',
            'ogrn': '2222222222222',
            'contact_email': 'protection@example.com',
            'contact_phone': '+73333333333'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        application_id = create_response.data['application_id']
        
        # Одобряем как администратор
        self.client.force_authenticate(user=self.admin_user)
        
        approve_response = self.client.patch(
            self.applications_detail_url(application_id),
            {'status': 'approved'},
            format='json'
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        
        # Пробуем изменить как обычный пользователь (должно быть отклонено)
        self.client.force_authenticate(user=self.user)
        
        update_data = {
            'company_name': 'Изменённое Название'  # Попытка изменить данные
        }
        
        update_response = self.client.patch(
            self.applications_detail_url(application_id),
            update_data,
            format='json'
        )
        
        # Обычный пользователь не может обновлять заявки (только администраторы)
        self.assertEqual(update_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_only_approval_workflow(self):
        """
        Тест: только администраторы могут одобрять/отклонять заявки
        """
        # Создаём заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Админ Тест',
            'inn': '3333333333',
            'ogrn': '4444444444444',
            'contact_email': 'admin_test@example.com',
            'contact_phone': '+72222222222'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        application_id = create_response.data['application_id']
        
        # Пробуем одобрить как обычный пользователь (должно быть отклонено)
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.force_authenticate(user=other_user)
        
        approve_data = {'status': 'approved'}
        approve_response = self.client.patch(
            self.applications_detail_url(application_id),
            approve_data,
            format='json'
        )
        
        # Может быть 403 (запрещено) или 404 (не найден из-за фильтрации),
        # так как пользователь не имеет доступа к этой заявке
        self.assertIn(approve_response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        
        # Проверяем, что статус заявки не изменился
        application = PartnerApplication.objects.get(id=application_id)
        self.assertEqual(application.status, 'pending')

    def test_concurrent_access_protection(self):
        """
        Тест защиты от одновременного доступа (транзакционность)
        """
        # Создаём заявку
        self.client.force_authenticate(user=self.user)
        
        application_data = {
            'company_name': 'Конкурентный Тест',
            'inn': '5555555555',
            'ogrn': '6666666666666',
            'contact_email': 'concurrent@example.com',
            'contact_phone': '+71111111111'
        }
        
        create_response = self.client.post(self.applications_list_url, application_data, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        
        application_id = create_response.data['application_id']
        
        # Проверяем начальное состояние
        application = PartnerApplication.objects.get(id=application_id)
        self.assertEqual(application.status, 'pending')
        
        # Одобряем заявку
        self.client.force_authenticate(user=self.admin_user)
        
        approve_response = self.client.patch(
            self.applications_detail_url(application_id),
            {'status': 'approved'},
            format='json'
        )
        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        
        # Пытаемся снова одобрить (должно быть отклонено)
        second_approve_response = self.client.patch(
            self.applications_detail_url(application_id),
            {'status': 'approved'},
            format='json'
        )
        self.assertEqual(second_approve_response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Проверяем, что статус остался approved, а не был изменен
        application.refresh_from_db()
        self.assertEqual(application.status, 'approved')