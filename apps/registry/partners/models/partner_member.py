# apps/registry/partners/models/partner_member.py
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from typing import Dict, List, TYPE_CHECKING, Optional

from apps.core.models.base import RegistryModel
from apps.registry.partners.models import Partner
from apps.registry.partners.permissions import get_partner_member_filter_for_user

if TYPE_CHECKING:
    from .partner_member import PartnerMember


class PartnerMemberQuerySet(models.QuerySet["PartnerMember"]):
    def for_user(self, user: User) -> "PartnerMemberQuerySet":
        """
        Фильтрует членов партнера по правам доступа.
        Использует общую логику из permissions.py.
        """
        q_filter = get_partner_member_filter_for_user(user)
        if q_filter is None:  # Суперпользователь
            return self
        return self.filter(q_filter)
    
    def active(self) -> "PartnerMemberQuerySet":
        """Возвращает только активных членов."""
        return self.filter(is_active=True)
    
    def for_partner(self, partner_id) -> "PartnerMemberQuerySet":
        """Фильтрует по конкретному партнеру."""
        return self.filter(partner_id=partner_id)
    
    def with_management_rights(self) -> "PartnerMemberQuerySet":
        """Возвращает членов с правами управления."""
        return self.filter(can_manage_members=True, is_active=True)


class PartnerMemberManager(models.Manager["PartnerMember"]):
    def get_queryset(self) -> PartnerMemberQuerySet:
        return PartnerMemberQuerySet(self.model, using=self._db)
    
    def for_user(self, user: User) -> PartnerMemberQuerySet:
        return self.get_queryset().for_user(user)
    
    def active(self) -> PartnerMemberQuerySet:
        return self.get_queryset().active()
    
    def for_partner(self, partner_id) -> PartnerMemberQuerySet:
        return self.get_queryset().for_partner(partner_id)


class PartnerMember(RegistryModel):
    """
    Модель члена/сотрудника партнерской организации.
    Позволяет связывать пользователей системы с партнерами и назначать роли.
    """
    # Определяем типы для статического анализатора
    if TYPE_CHECKING:
        def get_role_display(self) -> str: ...
    
    ROLE_EMPLOYEE = 'employee'
    ROLE_MANAGER = 'manager'
    ROLE_DIRECTOR = 'director'
    ROLE_ACCOUNTANT = 'accountant'
    ROLE_ADMIN = 'admin'
    
    ROLE_CHOICES = [
        (ROLE_EMPLOYEE, _('Сотрудник')),
        (ROLE_MANAGER, _('Менеджер')),
        (ROLE_DIRECTOR, _('Директор')),
        (ROLE_ACCOUNTANT, _('Бухгалтер')),
        (ROLE_ADMIN, _('Администратор партнера')),
    ]
    
    # Для удобства доступа к константам ролей
    @classmethod
    def get_role_choices(cls) -> List[tuple]:
        """Возвращает список ролей с переводами."""
        return cls.ROLE_CHOICES
    
    @classmethod
    def get_role_display_dict(cls) -> Dict[str, str]:
        """Возвращает словарь ролей для отображения."""
        return dict(cls.ROLE_CHOICES)
        
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_("Партнер"),
        help_text=_("Партнерская организация, к которой относится сотрудник")
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_memberships',
        verbose_name=_("Пользователь системы"),
        help_text=_("Привязка к пользователю системы (если есть аккаунт)")
    )
    
    employee_id = models.CharField(
        max_length=100,
        verbose_name=_("Табельный номер"),
        blank=True,
        null=True,
        help_text=_("Внутренний идентификатор сотрудника в партнерской организации")
    )
    
    work_email = models.EmailField(
        verbose_name=_("Рабочий email"),
        blank=True,
        null=True,
        help_text=_("Корпоративная почта сотрудника")
    )
    
    work_phone = models.CharField(
        max_length=100,
        verbose_name=_("Рабочий телефон"),
        blank=True,
        null=True,
        help_text=_("Корпоративный телефон")
    )
    
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default=ROLE_EMPLOYEE,
        verbose_name=_("Роль в партнерской организации"),
        help_text=_("Определяет уровень доступа и права в системе")
    )
    
    can_manage_members = models.BooleanField(
        default=False,
        verbose_name=_("Может управлять членами партнера"),
        help_text=_("Может добавлять/удалять других сотрудников партнера")
    )
    
    can_view_finance = models.BooleanField(
        default=False,
        verbose_name=_("Может просматривать финансы"),
        help_text=_("Доступ к финансовой информации партнера")
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Активный сотрудник"),
        help_text=_("Сотрудник активен в организации")
    )
    
    # Менеджер с support for_user() 
    objects: PartnerMemberManager = PartnerMemberManager() # type: ignore
    
    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Член партнера")
        verbose_name_plural = _("Члены партнеров")
        ordering = ['partner', 'name']
        indexes = [
            models.Index(fields=['partner', 'employee_id']),
            models.Index(fields=['partner', 'user']),
            models.Index(fields=['partner', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
        constraints = [
            # Уникальный табельный номер в рамках партнера
            models.UniqueConstraint(
                fields=['partner', 'employee_id'],
                name='unique_employee_per_partner',
                condition=models.Q(employee_id__isnull=False)
            ),
            # КОММЕНТИРУЕМ: пользователь может быть членом нескольких партнеров
            # models.UniqueConstraint(
            #     fields=['user'],
            #     name='unique_user_membership',
            #     condition=models.Q(user__isnull=False)
            # ),
        ]
    
    def __str__(self) -> str:
        if self.user:
            user_display = self.user.get_full_name() or self.user.username
            return f"{user_display} ({self.get_role_display()})"
        return f"{self.name} ({self.get_role_display()})"
    
    def clean(self) -> None:
        """
        Центральное место для model-level validation:
        - cross-field rules (например, либо email, либо phone обязателен)
        - application-level uniqueness checks (более дружелюбные ошибки)
        Не вызывайте save()/DB операции здесь.
        """        
        # 1) Вызов базовой логики (включая валидацию из mixin, если есть)
        super().clean()
        
        errors: Dict[str, List[str]] = {}
        
        # 2) Cross-field: Проверка обязательных полей
        if not self.name and not self.user:
            errors['name'] = [_("Заполните имя или привяжите пользователя")]
        
        # Проверка email или телефона
        if not self.work_email and not self.work_phone:
            errors.setdefault('work_email', []).append(
                _("Укажите рабочий email или телефон")
            )
        
        # 3) Application-level uniqueness checks (чтобы дать понятные ошибки до вставки в БД)
        # Владелец партнера не может быть его сотрудником, но может быть директором/админом (что логично)
        if (self.user and self.user == self.partner.owner and
            self.role not in ['director', 'admin']):
            errors['user'] = [_("Владелец партнера не может быть его сотрудником, но может быть директором или администратором")]
        
        # Автоматически даем права для высших ролей
        if self.role in ['director', 'admin']:
            self.can_manage_members = True
            self.can_view_finance = True
        
        if errors:
            raise ValidationError(errors) # type: ignore
    
    def save(self, *args, **kwargs):
        # Автозаполнение имени из пользователя
        if self.user and not self.name:
            self.name = self.user.get_full_name() or self.user.username
        
        super().save(*args, **kwargs)

    # Явно добавляем метод для статического анализатора
    def get_role_display(self) -> str:
        """Возвращает отображаемое значение роли с учетом перевода."""
        return dict(self.ROLE_CHOICES).get(self.role, self.role)

    @property
    def display_name(self) -> str:
        """Свойство для обратной совместимости."""
        return self.name
    
    @property
    def is_manager(self) -> bool:
        """Проверяет, является ли член менеджером."""
        return self.role in [
            self.ROLE_MANAGER, 
            self.ROLE_DIRECTOR, 
            self.ROLE_ADMIN
        ] or self.can_manage_members
    
    @property
    def role_display(self) -> str:
        """Альтернативное свойство для получения отображаемого значения роли."""
        return self.get_role_display()
    
    def has_permission(self, permission: str) -> bool:
        """Проверяет наличие конкретного разрешения."""
        if permission == 'manage_members':
            return self.can_manage_members
        elif permission == 'view_finance':
            return self.can_view_finance
        return False