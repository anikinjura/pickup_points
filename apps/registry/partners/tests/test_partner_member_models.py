# apps/registry/partners/tests/test_partner_member_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError

from apps.registry.partners.models import Partner, PartnerMember

User = get_user_model()


class PartnerMemberModelTest(TestCase):
    def setUp(self):
        self.owner1 = User.objects.create_user('owner1', 'owner1@example.com', 'password')
        self.owner2 = User.objects.create_user('owner2', 'owner2@example.com', 'password')
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'password')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'password')
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        
        self.partner1 = Partner.objects.create(
            name='ООО Тест 1', owner=self.owner1, inn='1234567890',
            ogrn='1234567890123', email='test1@example.com'
        )
        self.partner2 = Partner.objects.create(
            name='ООО Тест 2', owner=self.owner2, inn='0987654321',
            ogrn='3210987654321', email='test2@example.com'
        )
    
    def test_create_partner_member_with_user(self):
        """Тест создания члена партнера с пользователем."""
        member = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='test@example.com',
            role=PartnerMember.ROLE_MANAGER
        )
        self.assertEqual(member.partner, self.partner1)
        self.assertEqual(member.user, self.user1)
        self.assertEqual(member.role, PartnerMember.ROLE_MANAGER)
        self.assertTrue(member.is_active)
    
    def test_create_partner_member_without_user(self):
        """Тест создания члена партнера без пользователя."""
        member = PartnerMember.objects.create(
            partner=self.partner1,
            name='Иван Иванов',
            work_email='ivan@test.com',
            role=PartnerMember.ROLE_EMPLOYEE
        )
        self.assertEqual(member.partner, self.partner1)
        self.assertIsNone(member.user)
        self.assertEqual(member.name, 'Иван Иванов')
    
    def test_user_can_be_member_of_multiple_partners(self):
        """Тест: пользователь может быть членом нескольких партнеров."""
        member1 = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='user1@partner1.com'
        )
        member2 = PartnerMember.objects.create(
            partner=self.partner2,
            user=self.user1,
            work_email='user1@partner2.com'
        )
        self.assertEqual(member1.user, self.user1)
        self.assertEqual(member2.user, self.user1)
        self.assertEqual(PartnerMember.objects.filter(user=self.user1).count(), 2)
    
    def test_unique_employee_id_per_partner(self):
        """Тест: уникальный табельный номер в рамках партнера."""
        # Создаем первого члена
        member1 = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            employee_id='001',
            work_email='test1@example.com'
        )
        self.assertIsNotNone(member1)
        
        # Пытаемся создать второго члена с тем же employee_id в том же партнере
        # Используем отдельную транзакцию для изоляции ошибки
        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                PartnerMember.objects.create(
                    partner=self.partner1,
                    user=self.user2,
                    employee_id='001',  # Дубликат в том же партнере
                    work_email='test2@example.com'
                )
        
        # В другом партнере должен быть возможен такой же employee_id
        member3 = PartnerMember.objects.create(
            partner=self.partner2,
            user=self.user1,
            employee_id='001',  # Такой же номер в другом партнере
            work_email='test3@example.com'
        )
        self.assertIsNotNone(member3)
    
    def test_clean_validation_email_or_phone_required(self):
        """Тест валидации: email или телефон обязателен."""
        member = PartnerMember(
            partner=self.partner1,
            user=self.user1
        )
        with self.assertRaises(ValidationError) as context:
            member.full_clean()
        self.assertIn('work_email', context.exception.message_dict)
    
    def test_clean_validation_owner_cannot_be_member(self):
        """Тест: владелец партнера не может быть его сотрудником."""
        member = PartnerMember(
            partner=self.partner1,
            user=self.owner1,
            work_email='owner@test.com'
        )
        with self.assertRaises(ValidationError) as context:
            member.full_clean()
        self.assertIn('user', context.exception.message_dict)
    
    def test_automatic_permissions_for_director_and_admin(self):
        """Тест автоматического назначения прав для высших ролей."""
        # Директор
        director = PartnerMember(
            partner=self.partner1,
            user=self.user1,
            work_email='director@test.com',
            role=PartnerMember.ROLE_DIRECTOR
        )
        director.clean()
        self.assertTrue(director.can_manage_members)
        self.assertTrue(director.can_view_finance)
        
        # Администратор
        admin = PartnerMember(
            partner=self.partner1,
            user=self.user2,
            work_email='admin@test.com',
            role=PartnerMember.ROLE_ADMIN
        )
        admin.clean()
        self.assertTrue(admin.can_manage_members)
        self.assertTrue(admin.can_view_finance)
        
        # Сотрудник (должен остаться без прав)
        employee = PartnerMember(
            partner=self.partner1,
            user=self.user1,
            work_email='employee@test.com',
            role=PartnerMember.ROLE_EMPLOYEE
        )
        employee.clean()
        self.assertFalse(employee.can_manage_members)
        self.assertFalse(employee.can_view_finance)
    
    def test_for_user_method_owner(self):
        """Тест for_user для владельца партнера."""
        PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='user1@test.com'
        )
        PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user2,
            work_email='user2@test.com'
        )
        
        # Владелец видит всех своих членов
        members = PartnerMember.objects.for_user(self.owner1)
        self.assertEqual(members.count(), 2)
    
    def test_for_user_method_member(self):
        """Тест for_user для члена партнера."""
        member = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='user1@test.com'
        )
        
        # Член видит только себя
        members = PartnerMember.objects.for_user(self.user1)
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first(), member)
    
    def test_for_user_method_manager_with_rights(self):
        """Тест for_user для менеджера с правами."""
        # Менеджер с правами
        manager = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='manager@test.com',
            role=PartnerMember.ROLE_MANAGER,
            can_manage_members=True
        )
        # Обычный сотрудник
        employee = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user2,
            work_email='employee@test.com',
            role=PartnerMember.ROLE_EMPLOYEE
        )
        
        # Менеджер должен видеть всех членов своего партнера
        members = PartnerMember.objects.for_user(self.user1)
        self.assertEqual(members.count(), 2)
    
    def test_for_user_method_superuser(self):
        """Тест for_user для суперпользователя."""
        PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='user1@test.com'
        )
        PartnerMember.objects.create(
            partner=self.partner2,
            user=self.user2,
            work_email='user2@test.com'
        )
        
        # Суперпользователь видит всех
        members = PartnerMember.objects.for_user(self.admin)
        self.assertEqual(members.count(), 2)
    
    def test_is_manager_property(self):
        """Тест свойства is_manager."""
        member = PartnerMember(
            partner=self.partner1,
            user=self.user1,
            work_email='test@example.com'
        )
        
        member.role = PartnerMember.ROLE_MANAGER
        self.assertTrue(member.is_manager)
        
        member.role = PartnerMember.ROLE_EMPLOYEE
        member.can_manage_members = True
        self.assertTrue(member.is_manager)
    
    def test_get_role_display(self):
        """Тест метода get_role_display."""
        member = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            work_email='test@example.com',
            role=PartnerMember.ROLE_MANAGER
        )
        role_display = member.get_role_display()  # type: ignore
        self.assertEqual(role_display, 'Менеджер')
    
    def test_automatic_name_from_user(self):
        """Тест автозаполнения имени из пользователя."""
        # Создаем пользователя с полным именем
        user = User.objects.create_user(
            'fulluser', 'fulluser@example.com', 'password',
            first_name='Иван', last_name='Иванов'
        )
        member = PartnerMember.objects.create(
            partner=self.partner1,
            user=user,
            work_email='ivan@test.com'
        )
        # Имя должно заполниться автоматически при сохранении
        self.assertIn('Иван', member.name)
    
    def test_save_method_does_not_overwrite_existing_name(self):
        """Тест: save не перезаписывает существующее имя."""
        member = PartnerMember.objects.create(
            partner=self.partner1,
            user=self.user1,
            name='Кастомное имя',
            work_email='test@example.com'
        )
        self.assertEqual(member.name, 'Кастомное имя')