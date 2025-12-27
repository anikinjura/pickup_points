# apps/registry/partners/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from apps.registry.partners.models import Partner, PartnerMember
from apps.registry.partners.permissions import IsOwnerOrAdmin, IsPartnerMemberOwnerOrAdmin, check_partner_member_access, get_partner_member_filter_for_user

User = get_user_model()


class IsOwnerOrAdminPermissionTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsOwnerOrAdmin()
        
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
            is_staff=True,
            is_superuser=False
        )
        
        # Создаем партнера
        self.partner = Partner.objects.create(
            name='ООО Тест',
            owner=self.user1,
            inn='1234567890',
            ogrn='1234567890123',
            email='test@example.com'
        )

    def test_has_permission_authenticated_user(self):
        """Тест: аутентифицированный пользователь имеет доступ"""
        request = self.factory.get('/')
        request.user = self.user1
        
        has_perm = self.permission.has_permission(request, None)
        self.assertTrue(has_perm)

    def test_has_permission_unauthenticated_user(self):
        """Тест: неаутентифицированный пользователь не имеет доступа"""
        request = self.factory.get('/')
        request.user = None
        
        has_perm = self.permission.has_permission(request, None)
        self.assertFalse(has_perm)

    def test_has_object_permission_owner(self):
        """Тест: владелец имеет доступ к своему объекту"""
        request = self.factory.get('/')
        request.user = self.user1
        
        has_perm = self.permission.has_object_permission(request, None, self.partner)
        self.assertTrue(has_perm)

    def test_has_object_permission_non_owner(self):
        """Тест: не-владелец не имеет доступа к объекту"""
        request = self.factory.get('/')
        request.user = self.user2
        
        has_perm = self.permission.has_object_permission(request, None, self.partner)
        self.assertFalse(has_perm)

    def test_has_object_permission_admin(self):
        """Тест: admin имеет доступ к любому объекту"""
        request = self.factory.get('/')
        request.user = self.admin
        
        has_perm = self.permission.has_object_permission(request, None, self.partner)
        self.assertTrue(has_perm)

    def test_has_object_permission_staff_not_superuser(self):
        """Тест: staff (не superuser) не имеет доступа к чужому объекту"""
        request = self.factory.get('/')
        request.user = self.staff
        
        # Staff не должен иметь доступ к объекту, владельцем которого он не является
        has_perm = self.permission.has_object_permission(request, None, self.partner)
        self.assertFalse(has_perm, 
            "Staff пользователь без прав суперпользователя не должен иметь доступ к чужому объекту")

    def test_has_object_permission_staff_own_object(self):
        """Тест: staff имеет доступ к своему объекту"""
        # Создаем партнера для staff
        partner_staff = Partner.objects.create(
            name='ООО Staff',
            owner=self.staff,
            inn='5555555555',
            ogrn='5555555555555',
            email='staff@example.com'
        )
        
        request = self.factory.get('/')
        request.user = self.staff
        
        has_perm = self.permission.has_object_permission(request, None, partner_staff)
        self.assertTrue(has_perm)

class PartnerMemberPermissionsTest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsPartnerMemberOwnerOrAdmin()
        
        # Создаем пользователей
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'password')
        self.user1 = User.objects.create_user('user1', 'user1@example.com', 'password')
        self.user2 = User.objects.create_user('user2', 'user2@example.com', 'password')
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        
        # Создаем партнера
        self.partner = Partner.objects.create(
            name='ООО Тест', owner=self.owner,
            inn='1234567890', ogrn='1234567890123',
            email='test@example.com'
        )
        
        # Создаем членов партнера
        self.member1 = PartnerMember.objects.create(
            partner=self.partner,
            user=self.user1,
            work_email='user1@test.com',
            role=PartnerMember.ROLE_EMPLOYEE
        )
        self.member2 = PartnerMember.objects.create(
            partner=self.partner,
            user=self.user2,
            work_email='user2@test.com',
            role=PartnerMember.ROLE_MANAGER,
            can_manage_members=True
        )
    
    def test_check_partner_member_access_owner(self):
        """Тест: владелец имеет доступ к члену своего партнера."""
        self.assertTrue(check_partner_member_access(self.owner, self.member1))
    
    def test_check_partner_member_access_member_self(self):
        """Тест: член имеет доступ к своей записи."""
        self.assertTrue(check_partner_member_access(self.user1, self.member1))
    
    def test_check_partner_member_access_member_other(self):
        """Тест: член не имеет доступа к чужой записи."""
        self.assertFalse(check_partner_member_access(self.user1, self.member2))
    
    def test_check_partner_member_access_manager_with_rights(self):
        """Тест: менеджер с правами имеет доступ к другим членам."""
        # user2 - менеджер с правами
        self.assertTrue(check_partner_member_access(self.user2, self.member1))
    
    def test_check_partner_member_access_admin(self):
        """Тест: admin имеет доступ к любому члену."""
        self.assertTrue(check_partner_member_access(self.admin, self.member1))
    
    def test_check_partner_member_access_unauthenticated(self):
        """Тест: неаутентифицированный пользователь не имеет доступа."""
        self.assertFalse(check_partner_member_access(None, self.member1))
    
    def test_get_partner_member_filter_for_user_owner(self):
        """Тест фильтра для владельца."""
        q_filter = get_partner_member_filter_for_user(self.owner)
        members = PartnerMember.objects.filter(q_filter)
        self.assertEqual(members.count(), 2)  # Оба члена партнера
    
    def test_get_partner_member_filter_for_user_member(self):
        """Тест фильтра для члена."""
        q_filter = get_partner_member_filter_for_user(self.user1)
        members = PartnerMember.objects.filter(q_filter)
        self.assertEqual(members.count(), 1)
        self.assertEqual(members.first(), self.member1)
    
    def test_get_partner_member_filter_for_user_manager(self):
        """Тест фильтра для менеджера с правами."""
        q_filter = get_partner_member_filter_for_user(self.user2)
        members = PartnerMember.objects.filter(q_filter)
        self.assertEqual(members.count(), 2)  # Менеджер видит всех
    
    def test_get_partner_member_filter_for_user_admin(self):
        """Тест фильтра для суперпользователя."""
        q_filter = get_partner_member_filter_for_user(self.admin)
        self.assertIsNone(q_filter)  # Без фильтрации
    
    def test_is_partner_member_owner_or_admin_has_permission(self):
        """Тест has_permission для IsPartnerMemberOwnerOrAdmin."""
        request = self.factory.get('/')
        request.user = self.user1
        self.assertTrue(self.permission.has_permission(request, None))
    
    def test_is_partner_member_owner_or_admin_has_object_permission(self):
        """Тест has_object_permission для IsPartnerMemberOwnerOrAdmin."""
        request = self.factory.get('/')
        request.user = self.owner
        self.assertTrue(self.permission.has_object_permission(request, None, self.member1))