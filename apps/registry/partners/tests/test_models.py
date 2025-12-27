# apps/registry/partners/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.registry.partners.models import Partner

User = get_user_model()


class PartnerModelTest(TestCase):
    def setUp(self):
        """Настройка тестовых данных"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='user2@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123'
        )
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Создаем тестовых партнеров
        self.partner1 = Partner.objects.create(
            name='ООО Тест 1',
            owner=self.user1,
            inn='1234567890',
            ogrn='1234567890123',
            email='partner1@example.com'
        )
        self.partner2 = Partner.objects.create(
            name='ООО Тест 2',
            owner=self.user2,
            inn='0987654321',
            ogrn='3210987654321',
            phone='+79999999999'
        )
        self.partner_staff = Partner.objects.create(
            name='ООО Staff',
            owner=self.staff_user,
            inn='5555555555',
            ogrn='5555555555555',
            email='staff@company.com'
        )

    def test_create_partner(self):
        """Тест создания партнера"""
        self.assertEqual(self.partner1.name, 'ООО Тест 1')
        self.assertEqual(self.partner1.owner, self.user1)
        self.assertEqual(self.partner1.inn, '1234567890')
        self.assertFalse(self.partner1.validated)  # По умолчанию False

    def test_str_representation(self):
        """Тест строкового представления"""
        self.assertEqual(str(self.partner1), 'ООО Тест 1')
        self.assertEqual(str(self.partner2), 'ООО Тест 2')

    def test_clean_validation_email_or_phone_required(self):
        """Тест валидации: email или телефон обязателен"""
        partner = Partner(
            name='ООО Без контактов',
            owner=self.user1,
            inn='1212121212',
            ogrn='1212121212121'
        )
        
        with self.assertRaises(ValidationError) as context:
            partner.full_clean()
        
        self.assertIn('email', context.exception.message_dict)
        self.assertIn('Укажите email или телефон', 
                     context.exception.message_dict['email'])

    def test_clean_validation_only_email_passes(self):
        """Тест валидации: только email достаточно"""
        partner = Partner(
            name='ООО Только email',
            owner=self.user1,
            inn='1313131313',
            ogrn='1313131313131',
            email='test@example.com'
        )
        
        try:
            partner.full_clean()
        except ValidationError:
            self.fail("Партнер с только email должен пройти валидацию")

    def test_clean_validation_only_phone_passes(self):
        """Тест валидации: только телефон достаточно"""
        partner = Partner(
            name='ООО Только телефон',
            owner=self.user1,
            inn='1414141414',
            ogrn='1414141414141',
            phone='+79998887766'
        )
        
        try:
            partner.full_clean()
        except ValidationError:
            self.fail("Партнер с только телефоном должен пройти валидацию")

    def test_clean_validation_duplicate_inn(self):
        """Тест валидации: дубликат ИНН"""
        partner = Partner(
            name='ООО Дубликат ИНН',
            owner=self.user1,
            inn='1234567890',  # Дубликат partner1
            ogrn='9999999999999',
            email='duplicate@example.com'
        )
        
        with self.assertRaises(ValidationError) as context:
            partner.full_clean()
        
        self.assertIn('inn', context.exception.message_dict)
        self.assertIn('Партнер с таким ИНН уже существует', 
                     context.exception.message_dict['inn'])

    def test_clean_validation_duplicate_ogrn(self):
        """Тест валидации: дубликат ОГРН"""
        partner = Partner(
            name='ООО Дубликат ОГРН',
            owner=self.user1,
            inn='9999999999',
            ogrn='1234567890123',  # Дубликат partner1
            email='duplicate@example.com'
        )
        
        with self.assertRaises(ValidationError) as context:
            partner.full_clean()
        
        self.assertIn('ogrn', context.exception.message_dict)
        self.assertIn('Партнер с таким ОГРН уже существует', 
                     context.exception.message_dict['ogrn'])

    def test_mark_validated_method(self):
        """Тест метода mark_validated"""
        self.assertFalse(self.partner1.validated)
        self.assertIsNone(self.partner1.validated_at)
        
        self.partner1.mark_validated()
        
        self.assertTrue(self.partner1.validated)
        self.assertIsNotNone(self.partner1.validated_at)
        self.assertIsInstance(self.partner1.validated_at, timezone.datetime)

    def test_for_user_method_user1(self):
        """Тест метода for_user для обычного пользователя"""
        partners = Partner.objects.for_user(self.user1)
        self.assertEqual(partners.count(), 1)
        self.assertEqual(partners.first(), self.partner1)

    def test_for_user_method_user2(self):
        """Тест метода for_user для другого пользователя"""
        partners = Partner.objects.for_user(self.user2)
        self.assertEqual(partners.count(), 1)
        self.assertEqual(partners.first(), self.partner2)

    def test_for_user_method_admin(self):
        """Тест метода for_user для суперпользователя"""
        partners = Partner.objects.for_user(self.admin_user)
        self.assertEqual(partners.count(), 3)  # Все партнеры

    def test_for_user_method_staff(self):
        """Тест метода for_user для staff пользователя"""
        partners = Partner.objects.for_user(self.staff_user)
        self.assertEqual(partners.count(), 1)
        self.assertEqual(partners.first(), self.partner_staff)

    def test_queryset_chaining(self):
        """Тест цепочки методов QuerySet"""
        partners = Partner.objects.for_user(self.user1).filter(name__contains='Тест')
        self.assertEqual(partners.count(), 1)
        
        partners_sorted = Partner.objects.for_user(self.admin_user).order_by('name')
        self.assertEqual(partners_sorted.count(), 3)
        self.assertEqual(partners_sorted.first().name, 'ООО Staff')

    def test_queryset_type(self):
        """Тест типа возвращаемого значения for_user"""
        from apps.registry.partners.models.partner import PartnerQuerySet
        queryset = Partner.objects.for_user(self.user1)
        self.assertIsInstance(queryset, PartnerQuerySet)

    def test_model_meta(self):
        """Тест Meta опций модели"""
        self.assertEqual(Partner._meta.verbose_name, 'Партнёр')
        self.assertEqual(Partner._meta.verbose_name_plural, 'Партнёры')
        self.assertEqual(Partner._meta.ordering, ['name'])