"""
apps/registry/partners/permissions.py - центральный модуль для всей логики прав доступа

Архитектура централизованной фильтрации:
1. Фильтрация данных через Q-объекты для QuerySet-ов
2. Проверка доступа к отдельным объектам
3. DRF-интеграция через Permission классы

Структура:
apps/registry/partners/
├── permissions.py                              # ← ЦЕНТРАЛИЗОВАННАЯ логика доступа
│   ├── get_*_filter_for_user()                # Возвращают Q-объекты для фильтрации QuerySet-ов
│   │   ├── get_partner_filter_for_user()      # Фильтр для PartnerQuerySet
│   │   ├── get_partner_member_filter_for_user() # Фильтр для PartnerMemberQuerySet
│   │   └── get_partner_application_filter_for_user() # Фильтр для PartnerApplicationQuerySet
│   ├── check_*_access()                       # Проверка доступа к конкретным объектам
│   │   ├── check_partner_access()             # Доступ к Partner
│   │   ├── check_partner_member_access()      # Доступ к PartnerMember
│   │   └── check_partner_application_access() # Доступ к PartnerApplication
│   └── DRF Permission классы                  # Для view-level проверок
├── models/                                    # ← Используют центральную логику
│   ├── partner.py                             # PartnerQuerySet.for_user() → get_partner_filter_for_user()
│   ├── partner_member.py                      # PartnerMemberQuerySet.for_user() → get_partner_member_filter_for_user()
│   └── partner_application.py                 # PartnerApplicationQuerySet.for_user() → get_partner_application_filter_for_user()
├── views/                                     # ← Работают через QuerySet-ы
│   ├── partner_viewset.py                     # get_queryset() → Partner.objects.for_user(user)
│   ├── partner_member_viewset.py              # get_queryset() → PartnerMember.objects.for_user(user)
│   └── application_viewset.py                 # get_queryset() → PartnerApplication.objects.for_user(user)
└── ...

Принципы:
- Единая точка истины для логики доступа
- Консистентное использование Q-объектов
- Защита от циклических импортов через локальные импорты
- DRF-ready: легко добавлять новые модели с .for_user() методом
"""
from typing import Optional, Dict, Any
from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import permissions

# ==================== ОБЩИЕ УТИЛИТНЫЕФУНКЦИИ ДЛЯ ЛОГИКИ ДОСТУПА КPARTNER ====================
def get_partner_filter_for_user(user: User) -> Optional[Q]:
    """
    Возвращает Q-объект для фильтрации QuerySet для пользователя.
    None = без фильтрация (суперпользователь).
    Q(pk__in=[]) = нет записей (неаутентифицированный).
    """
    if user is None or not user.is_authenticated:
        return Q(pk__in=[])  # Гарантированно пустой результат

    if user.is_superuser:
        return None  # Без фильтрации

    # Для сохранения совместимости с существующими тестами:
    # пользователи видят только партнёров, которыми они владеют
    # Это централизованная точка для этой логики
    return Q(owner=user)


def check_partner_access(user: User, partner) -> bool:
    """
    Проверяет, имеет ли пользователь доступ к конкретному партнеру.
    """
    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    return getattr(partner, 'owner', None) == user


# ==================== ОБЩИЕ УТИЛИТНЫЕ ФУНКЦИИ ДЛЯ ДОСТУПА К PARTNER MEMBER ====================
def get_partner_member_filter_for_user(user: User) -> Optional[Q]:
    """
    Возвращает Q-объект для фильтрации QuerySet членов партнера.
    None = без фильтрации (суперпользователь).
    Q(pk__in=[]) = нет записей (неаутентифицированный).
    """
    # ЛОКАЛЬНЫЙ импорт для избежания циклических зависимостей
    from apps.registry.partners.models import PartnerMember

    if user is None or not user.is_authenticated:
        return Q(pk__in=[])

    if user.is_superuser:
        return None

    # Базовое условие: владелец партнера видит всех членов своих партнеров
    # ИЛИ пользователь видит свои собственные членства
    q_filter = Q(partner__owner=user) | Q(user=user)

    # Дополнительно: если пользователь - менеджер с правами управления членами,
    # он видит всех членов партнера, в котором имеет такие права
    managing_memberships = PartnerMember.objects.filter(
        user=user,
        can_manage_members=True,
        is_active=True
    ).select_related('partner')

    for membership in managing_memberships:
        # Добавляем условие для партнера, в котором пользователь имеет права
        q_filter |= Q(partner=membership.partner)

    return q_filter


def check_partner_member_access(user: User, member) -> bool:
    """
    Проверяет доступ пользователя к члену партнера.
    """
    # ЛОКАЛЬНЫЙ импорт для избежания циклических зависимостей
    from apps.registry.partners.models import PartnerMember

    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Владелец партнера (т.е. сам партнер) имеет доступ к своим членам
    if member.partner.owner == user:
        return True

    # Член партнера имеет доступ к своей записи
    if member.user == user:
        return True

    # Менеджеры с правами могут видеть других членов своего партнера
    # Проверяем, есть ли у пользователя активное членство с правами управления в том же партнере
    return PartnerMember.objects.filter(
        user=user,
        partner=member.partner,
        can_manage_members=True,
        is_active=True
    ).exists()


def check_partner_member_management_access(user: User, partner) -> bool:
    """
    Проверяет, имеет ли пользователь права на управление членами партнера.
    Используется для операций создания/редактирования членов партнера.
    """
    # ЛОКАЛЬНЫЙ импорт для избежания циклических зависимостей
    from apps.registry.partners.models import PartnerMember

    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Владелец партнера может управлять членами
    if partner.owner == user:
        return True

    # Пользователь с правами управления членами может управлять членами партнера
    return PartnerMember.objects.filter(
        user=user,
        partner=partner,
        can_manage_members=True,
        is_active=True
    ).exists()


# ==================== УТИЛИТНЫЕ ФУНКЦИИ ДЛЯ ДОСТУПА К PARTNER APPLICATION ====================
def get_partner_application_filter_for_user(user: User) -> Optional[Q]:
    """
    Возвращает Q-объект для фильтрации QuerySet заявок партнера.
    None = без фильтрации (суперпользователь).
    Q(pk__in=[]) = нет записей (неаутентифицированный).
    """
    if user is None or not user.is_authenticated:
        return Q(pk__in=[])

    if user.is_superuser:
        return None

    # Обычный пользователь видит только свои заявки
    return Q(user=user)


def check_partner_application_access(user: User, application) -> bool:
    """
    Проверяет доступ пользователя к конкретной заявке.
    """
    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    # Пользователь имеет доступ к своей заявке
    return application.user == user


# ==================== УТИЛИТНЫЕ ФУНКЦИИ ДЛЯ ДОСТУПА К PICKUP POINT ====================
def get_pickup_point_filter_for_user(user: User) -> Optional[Q]:
    """
    Возвращает Q-объект для фильтрации QuerySet пунктов выдачи.
    None = без фильтрации (суперпользователь).
    Q(pk__in=[]) = нет записей (неаутентифицированный).
    """
    if user is None or not user.is_authenticated:
        return Q(pk__in=[])

    if user.is_superuser or user.is_staff:
        return None

    # Владелец партнера видит ПВЗ своих партнеров
    # Члены партнера видят ПВЗ своего партнера
    q_filter = Q(partner__owner=user)

    # Добавляем ПВЗ, к которым имеют доступ члены партнера
    # ЛОКАЛЬНЫЙ импорт для избежания циклических зависимостей
    from apps.registry.partners.models import PartnerMember

    partner_members = PartnerMember.objects.filter(
        user=user,
        is_active=True
    ).select_related('partner')

    for member in partner_members:
        q_filter |= Q(partner=member.partner)

    return q_filter


def check_pickup_point_access(user: User, pickup_point) -> bool:
    """
    Проверяет доступ пользователя к конкретному ПВЗ.
    """
    # ЛОКАЛЬНЫЙ импорт для избежания циклических зависимостей
    from apps.registry.partners.models import PartnerMember

    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    # Владелец партнера имеет доступ к ПВЗ своего партнера
    if pickup_point.partner.owner == user:
        return True

    # Активные члены партнера имеют доступ к ПВЗ партнера
    return PartnerMember.objects.filter(
        user=user,
        partner=pickup_point.partner,
        is_active=True
    ).exists()


def check_pickup_point_crud_access(user: User, pickup_point) -> bool:
    """
    Проверяет права на CRUD операции с ПВЗ.
    """
    if user is None or not user.is_authenticated:
        return False

    if user.is_superuser or user.is_staff:
        return True

    # Владелец партнера может CRUD ПВЗ своего партнера
    if pickup_point.partner.owner == user:
        return True

    return False


def validate_partner_pickup_point_access(user: User, partner) -> bool:
    """
    Проверяет, может ли пользователь создавать/обновлять ПВЗ для партнера.
    Включает проверку прав доступа к партнеру и статуса партнера.
    """
    # Проверяем права доступа к партнеру
    if not check_partner_access(user, partner):
        return False

    # Проверяем статус партнера
    if not partner.validated:
        return False

    return True


def validate_partner_member_pickup_point_relationship(partner, pickup_point) -> bool:
    """
    Проверяет, что пункт выдачи принадлежит тому же партнеру, что и член партнера.
    """
    if pickup_point and pickup_point.partner != partner:
        return False
    return True

# ==================== DRF PERMISSION КЛАССЫ ====================
class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает доступ владельцу объекта (obj.owner == request.user) или superuser.
    """

    def has_permission(self, request, view):
        # Проверка на уровне view (публичный доступ запрещён по умолчанию в проекте).
        # Оставляем базовую проверку: пользователь должен быть аутентифицирован.
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj): # type: ignore
        # Явно приводим к bool и игнорируем проверку типов
        return bool(check_partner_access(request.user, obj))

class IsPartnerMemberOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает доступ владельцу партнера, самому члену, менеджеру с правами или суперпользователю.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj): # type: ignore
        return bool(check_partner_member_access(request.user, obj))

class IsPickupPointOwnerOrAdmin(permissions.BasePermission):
    """
    Разрешает CRUD доступ владельцу партнера, staff или superuser.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj): # type: ignore
        return bool(check_pickup_point_crud_access(request.user, obj))