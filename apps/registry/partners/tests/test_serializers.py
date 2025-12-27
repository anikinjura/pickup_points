# apps/registry/partners/tests/test_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.registry.partners.models import Partner
from apps.registry.partners.serializers import PartnerSerializer

User = get_user_model()


class PartnerSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.partner = Partner.objects.create(
            name='ООО Существующий',
            owner=self.user,
            inn='1234567890',
            ogrn='1234567890123',
            email='existing@example.com'
        )

    def test_valid_serializer_data(self):
        """Тест валидных данных"""
        data = {
            'name': 'ООО Тест',
            'inn': '7777777777',
            'ogrn': '7777777777777',
            'email': 'test@example.com',
        }
        
        serializer = PartnerSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['name'], 'ООО Тест')
        self.assertEqual(serializer.validated_data['inn'], '7777777777')

    def test_invalid_inn_serializer(self):
        """Тест невалидного ИНН"""
        data = {
            'name': 'ООО Неправильный ИНН',
            'inn': '123',  # Слишком короткий
            'ogrn': '5555555555555',
            'phone': '+76666666666',
        }
        
        serializer = PartnerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('inn', serializer.errors)

    def test_no_contacts_serializer(self):
        """Тест отсутствия контактов"""
        data = {
            'name': 'ООО Без контактов',
            'inn': '6666666666',
            'ogrn': '6666666666666',
        }
        
        serializer = PartnerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)

    def test_duplicate_inn_serializer(self):
        """Тест дубликата ИНН через сериализатор"""
        data = {
            'name': 'ООО Дубликат',
            'inn': '1234567890',  # Дубликат существующего
            'ogrn': '8888888888888',
            'email': 'duplicate@example.com',
        }
        
        serializer = PartnerSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('inn', serializer.errors)

    def test_update_serializer(self):
        """Тест обновления через сериализатор"""
        data = {'name': 'ООО Обновленное название'}
        
        serializer = PartnerSerializer(
            instance=self.partner, 
            data=data, 
            partial=True
        )
        
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.name, 'ООО Обновленное название')

    def test_read_only_fields(self):
        """Тест read_only полей"""
        data = {
            'name': 'ООО Тест',
            'inn': '9999999999',
            'ogrn': '9999999999999',
            'email': 'test@example.com',
            'owner': 999,  # Пытаемся установить владельца
            'validated': True,  # Пытаемся изменить read_only поле
        }
        
        serializer = PartnerSerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save(owner=self.user)
            # Проверяем, что owner установлен правильно, а не из данных
            self.assertEqual(instance.owner, self.user)
            # Проверяем, что validated остался False (значение по умолчанию)
            self.assertFalse(instance.validated)

    def test_serializer_fields(self):
        """Тест полей сериализатора"""
        serializer = PartnerSerializer(instance=self.partner)
        
        expected_fields = [
            'id', 'name', 'owner', 'email', 'phone', 'legal_form',
            'inn', 'ogrn', 'kpp', 'address', 'validated', 'validated_at',
            'created_at', 'updated_at'
        ]
        
        for field in expected_fields:
            self.assertIn(field, serializer.data)