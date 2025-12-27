# apps/registry/partners/tests/test_partner_member_serializers.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.registry.partners.models import Partner, PartnerMember
from apps.registry.partners.serializers import PartnerMemberSerializer

User = get_user_model()


class PartnerMemberSerializerTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'password')
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'password')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'password')
        
        self.partner = Partner.objects.create(
            name='ООО Тест', owner=self.owner,
            inn='1234567890', ogrn='1234567890123',
            email='test@example.com'
        )
        
        self.member = PartnerMember.objects.create(
            partner=self.partner,
            user=self.user1,
            work_email='user1@test.com',
            role=PartnerMember.ROLE_MANAGER
        )
    
    def test_valid_serializer_data(self):
        """Тест валидных данных."""
        data = {
            'partner': self.partner.id,
            'user': self.user2.id,
            'work_email': 'new@test.com',
            'role': PartnerMember.ROLE_EMPLOYEE,
            'name': '',
        }
        serializer = PartnerMemberSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_invalid_no_contact_info(self):
        """Тест отсутствия контактной информации."""
        data = {
            'partner': self.partner.id,
            'user': self.user2.id,
            'role': PartnerMember.ROLE_EMPLOYEE,
            'name': '',
        }
        serializer = PartnerMemberSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # Теперь ошибка должна быть в work_email
        self.assertIn('work_email', serializer.errors)
    
    def test_serializer_read_only_fields(self):
        """Тест read_only полей."""
        serializer = PartnerMemberSerializer(instance=self.member)
        data = serializer.data
        
        # Проверяем наличие read_only полей
        self.assertIn('partner_name', data)
        self.assertIn('user_email', data)
        self.assertIn('user_username', data)
        self.assertIn('role_display', data)
        self.assertIn('created_at', data)
        self.assertIn('updated_at', data)
    
    def test_serializer_update(self):
        """Тест обновления через сериализатор."""
        data = {
            'work_email': 'new_email@test.com',
            'work_phone': '+79998887766'
        }
        serializer = PartnerMemberSerializer(
            instance=self.member,
            data=data,
            partial=True
        )
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.work_email, 'new_email@test.com')
        self.assertEqual(updated.work_phone, '+79998887766')
    
    def test_serializer_role_choices_validation(self):
        """Тест валидации ролей."""
        data = {
            'partner': self.partner.id,
            'user': self.user2.id,
            'work_email': 'test@test.com',
            'role': 'invalid_role'  # Несуществующая роль
        }
        serializer = PartnerMemberSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('role', serializer.errors)
    
    def test_serializer_without_user_requires_name(self):
        """Тест: при создании без пользователя требуется имя."""
        data = {
            'partner': self.partner.id,
            'work_email': 'test@test.com',
            'role': PartnerMember.ROLE_EMPLOYEE
            # Нет имени и пользователя
        }
        serializer = PartnerMemberSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('name', serializer.errors)
    
    def test_serializer_name_autofill_from_user(self):
        """Тест автозаполнения имени из пользователя при сохранении."""
        # Создаем пользователя с именем
        user = User.objects.create_user(
            'testuser', 'test@example.com', 'password',
            first_name='Иван', last_name='Иванов'
        )
        data = {
            'partner': self.partner.id,
            'user': user.id,
            'work_email': 'ivan@test.com',
            'role': PartnerMember.ROLE_EMPLOYEE,
            'name': '',
        }
        serializer = PartnerMemberSerializer(data=data)
        self.assertTrue(serializer.is_valid()) # должно быть True
        member = serializer.save()
        # Имя должно заполниться автоматически
        self.assertIn('Иван', member.name)