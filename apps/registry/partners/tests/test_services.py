# apps/registry/partners/tests/test_services.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.utils import timezone

from apps.registry.partners.models import Partner, PartnerMember, PartnerApplication
from apps.registry.partners.services.partner_service import (
    create_partner,
    create_partner_from_application,
    create_initial_partner_member,
    update_application_status,
    approve_partner_application,
    reject_partner_application
)

User = get_user_model()


class PartnerServiceTest(TestCase):
    def setUp(self):
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

        # Существующий партнер для тестов дубликатов
        self.existing_partner = Partner.objects.create(
            name='ООО Существующий',
            owner=self.user,
            inn='1234567890',
            ogrn='1234567890123',
            email='existing@example.com'
        )

        # Тестовая заявка для тестирования атомарных операций
        self.test_application = PartnerApplication.objects.create(
            user=self.user,
            company_name='ООО Тестовая Компания',
            inn='1111111111',
            ogrn='1111111111111',
            contact_email='test@example.com',
            contact_phone='+79999999999',
            status='pending'
        )

    def test_create_partner_success(self):
        """Тест успешного создания партнера через сервис"""
        data = {
            'name': 'ООО Сервис Тест',
            'inn': '7777777777',
            'ogrn': '7777777777777',
            'email': 'service_test@example.com',
            'phone': '+75555555555',
        }
        
        partner = create_partner(data, self.user)
        
        self.assertIsInstance(partner, Partner)
        self.assertEqual(partner.name, 'ООО Сервис Тест')
        self.assertEqual(partner.owner, self.user)
        self.assertEqual(partner.inn, '7777777777')

    def test_create_partner_duplicate_inn(self):
        """Тест создания партнера с дубликатом ИНН через сервис"""
        data = {
            'name': 'ООО Дубликат',
            'inn': '1234567890',  # Дубликат
            'ogrn': '9999999999999',
            'email': 'duplicate@example.com',
        }
        
        with self.assertRaises(DRFValidationError):
            create_partner(data, self.user)

    def test_create_partner_no_contacts(self):
        """Тест создания партнера без контактов через сервис"""
        data = {
            'name': 'ООО Без контактов',
            'inn': '1212121212',
            'ogrn': '1212121212121',
        }
        
        with self.assertRaises(DRFValidationError):
            create_partner(data, self.user)

    def test_create_partner_invalid_inn(self):
        """Тест создания партнера с невалидным ИНН через сервис"""
        data = {
            'name': 'ООО Невалидный ИНН',
            'inn': '123',  # Невалидный
            'ogrn': '5555555555555',
            'phone': '+76666666666',
        }
        
        with self.assertRaises(DRFValidationError):
            create_partner(data, self.user)

    def test_create_partner_integrity_error_handling(self):
        """Тест обработки IntegrityError в сервисе"""
        # Создаем двух пользователей
        user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )

        # Создаем партнера от первого пользователя
        data1 = {
            'name': 'ООО Первый',
            'inn': '8888888888',  # Уникальный ИНН
            'ogrn': '8888888888888',
            'email': 'first@example.com',
        }
        partner1 = create_partner(data1, self.user)

        # Пытаемся создать партнера с тем же ИНН от второго пользователя
        # Это вызовет IntegrityError из-за unique constraint
        data2 = {
            'name': 'ООО Второй',
            'inn': '8888888888',  # Тот же ИНН
            'ogrn': '9999999999999',
            'email': 'second@example.com',
        }

        # Сервис должен перехватить IntegrityError и превратить в ValidationError
        with self.assertRaises(DRFValidationError):
            create_partner(data2, user2)

    def test_create_partner_from_application_success(self):
        """Тест создания партнера из заявки"""
        partner = create_partner_from_application(self.test_application)

        self.assertIsInstance(partner, Partner)
        self.assertEqual(partner.name, self.test_application.company_name)
        self.assertEqual(partner.inn, self.test_application.inn)
        self.assertEqual(partner.ogrn, self.test_application.ogrn)
        self.assertEqual(partner.email, self.test_application.contact_email)
        self.assertEqual(partner.phone, self.test_application.contact_phone)
        self.assertEqual(partner.owner, self.test_application.user)

    def test_create_initial_partner_member_success(self):
        """Тест создания начального членства (владельца)"""
        partner = Partner.objects.create(
            name='ООО Тестовый Партнер',
            owner=self.user,
            inn='2222222222',
            ogrn='2222222222222',
            email='new@example.com',
            phone='+78888888888'
        )

        member = create_initial_partner_member(partner, self.user, self.test_application)

        self.assertIsInstance(member, PartnerMember)
        self.assertEqual(member.partner, partner)
        self.assertEqual(member.user, self.user)
        self.assertEqual(member.role, 'director')
        self.assertEqual(member.name, self.user.get_full_name() or self.user.username)
        self.assertEqual(member.work_email, self.test_application.contact_email)
        self.assertEqual(member.work_phone, self.test_application.contact_phone)

    def test_update_application_status_success(self):
        """Тест обновления статуса заявки"""
        initial_status = self.test_application.status
        initial_processed_at = self.test_application.processed_at
        initial_processed_by = self.test_application.processed_by

        # Обновляем статус
        updated_application = update_application_status(
            self.test_application,
            'approved',
            self.admin_user,
            'Тестовое одобрение'
        )

        # Проверяем, что статус обновлён
        self.assertEqual(updated_application.status, 'approved')
        self.assertEqual(updated_application.processed_by, self.admin_user)
        self.assertEqual(updated_application.rejection_reason, 'Тестовое одобрение')
        # Дата обновления должна быть заполнена
        self.assertIsNotNone(updated_application.processed_at)
        # Убедимся, что новая дата не раньше старой
        if initial_processed_at:
            self.assertGreaterEqual(updated_application.processed_at, initial_processed_at)

    def test_update_application_status_rejection_without_reason(self):
        """Тест обновления статуса заявки с отклонением без причины"""
        updated_application = update_application_status(
            self.test_application,
            'rejected',
            self.admin_user
        )

        # Должно обновиться без ошибки, причина None
        self.assertEqual(updated_application.status, 'rejected')
        self.assertEqual(updated_application.processed_by, self.admin_user)
        # Проверяем, что processed_at устанавливется
        self.assertIsNotNone(updated_application.processed_at)

    def test_approve_partner_application_success(self):
        """Тест полного процесса одобрения заявки"""
        # Сохраняем начальное состояние
        initial_application_status = self.test_application.status

        # Одобряем заявку
        partner, owner_member = approve_partner_application(self.test_application, self.admin_user)

        # Проверяем созданный партнёр
        self.assertIsInstance(partner, Partner)
        self.assertEqual(partner.name, self.test_application.company_name)
        self.assertEqual(partner.owner, self.test_application.user)
        self.assertEqual(partner.email, self.test_application.contact_email)
        self.assertEqual(partner.phone, self.test_application.contact_phone)

        # Проверяем созданное членство
        self.assertIsInstance(owner_member, PartnerMember)
        self.assertEqual(owner_member.partner, partner)
        self.assertEqual(owner_member.user, self.test_application.user)
        self.assertEqual(owner_member.role, 'director')

        # Проверяем обновлённую заявку
        self.test_application.refresh_from_db()
        self.assertEqual(self.test_application.status, 'approved')
        self.assertEqual(self.test_application.processed_by, self.admin_user)
        self.assertEqual(self.test_application.partner, partner)
        self.assertIsNotNone(self.test_application.processed_at)

    def test_approve_partner_application_not_pending_error(self):
        """Тест ошибки при попытке одобрить не-pending заявку"""
        # Сначала отклоним заявку
        reject_partner_application(self.test_application, self.admin_user, 'Тестовое отклонение')

        # Теперь попробуем одобрить уже отклонённую заявку
        with self.assertRaises(DRFValidationError):
            approve_partner_application(self.test_application, self.admin_user)

    def test_reject_partner_application_success(self):
        """Тест полного процесса отклонения заявки"""
        # Сохраняем начальное состояние
        initial_application_status = self.test_application.status

        # Отклоняем заявку
        updated_application = reject_partner_application(
            self.test_application,
            self.admin_user,
            'Тестовая причина отклонения'
        )

        # Проверяем обновлённую заявку
        self.assertEqual(updated_application.status, 'rejected')
        self.assertEqual(updated_application.processed_by, self.admin_user)
        self.assertEqual(updated_application.rejection_reason, 'Тестовая причина отклонения')
        self.assertIsNotNone(updated_application.processed_at)

        # Проверяем, что в БД изменения сохранились
        self.test_application.refresh_from_db()
        self.assertEqual(self.test_application.status, 'rejected')
        self.assertEqual(self.test_application.processed_by, self.admin_user)
        self.assertEqual(self.test_application.rejection_reason, 'Тестовая причина отклонения')
        self.assertIsNotNone(self.test_application.processed_at)

    def test_reject_partner_application_not_pending_error(self):
        """Тест ошибки при попытке отклонить не-pending заявку"""
        # Сначала одобрим заявку
        approve_partner_application(self.test_application, self.admin_user)

        # Теперь попробуем отклонить уже одобренную заявку
        with self.assertRaises(DRFValidationError):
            reject_partner_application(self.test_application, self.admin_user, 'Тестовое отклонение')