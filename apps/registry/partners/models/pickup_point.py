# apps/registry/partners/models/pickup_point.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from typing import Dict, List, TYPE_CHECKING

from apps.core.models.base import RegistryModel
from apps.registry.partners.models.partner import Partner
from apps.registry.partners.models.partner_member import PartnerMember
from apps.registry.partners.permissions import get_pickup_point_filter_for_user

if TYPE_CHECKING:
    from .pickup_point import PickupPoint


class PickupPointQuerySet(models.QuerySet["PickupPoint"]):
    def for_user(self, user):
        """
        Фильтрует пункты выдачи по правам доступа.
        Использует общую логику из permissions.py.
        """
        q_filter = get_pickup_point_filter_for_user(user)
        if q_filter is None:  # Суперпользователь
            return self
        return self.filter(q_filter)

    def for_partner(self, partner_id) -> "PickupPointQuerySet":
        """Фильтрует по конкретному партнеру."""
        return self.filter(partner_id=partner_id)

    def active(self) -> "PickupPointQuerySet":
        """Возвращает только активные ПВЗ."""
        return self.filter(is_active=True)


class PickupPointManager(models.Manager["PickupPoint"]):
    def get_queryset(self) -> PickupPointQuerySet:
        return PickupPointQuerySet(self.model, using=self._db)

    def for_user(self, user) -> PickupPointQuerySet:
        return self.get_queryset().for_user(user)

    def for_partner(self, partner_id) -> PickupPointQuerySet:
        return self.get_queryset().for_partner(partner_id)

    def active(self) -> PickupPointQuerySet:
        return self.get_queryset().active()


class PickupPoint(RegistryModel):
    """
    Модель пункта выдачи заказов (ПВЗ).
    Описывает физическое место выдачи заказов для партнера.
    """
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='pickup_points',
        verbose_name=_("Партнер"),
        help_text=_("Партнерская организация, которой принадлежит ПВЗ")
    )

    address = models.TextField(
        verbose_name=_("Адрес"),
        help_text=_("Полный адрес пункта выдачи заказов")
    )

    location_details = models.CharField(
        max_length=255,
        verbose_name=_("Расположение"),
        blank=True,
        null=True,
        help_text=_("Детали расположения (например: цокольный этаж, 1-ый этаж)")
    )

    work_schedule = models.CharField(
        max_length=255,
        verbose_name=_("График работы"),
        help_text=_("График работы ПВЗ (например: с 9:00 до 21:00)")
    )

    phone = models.CharField(
        max_length=100,
        verbose_name=_("Телефон"),
        blank=True,
        null=True,
        help_text=_("Контактный телефон ПВЗ")
    )

    email = models.EmailField(
        verbose_name=_("Email"),
        blank=True,
        null=True,
        help_text=_("Контактный email ПВЗ")
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Активный"),
        help_text=_("ПВЗ активен для использования")
    )

    # Менеджер с support for_user()
    objects: PickupPointManager = PickupPointManager()  # type: ignore

    class Meta:
        verbose_name = _("Пункт выдачи заказов")
        verbose_name_plural = _("Пункты выдачи заказов")
        ordering = ['partner', 'name']
        indexes = [
            models.Index(fields=['partner', 'is_active']),
            models.Index(fields=['partner', 'name']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.partner.name})"

    def clean(self) -> None:
        """
        Центральное место для model-level validation:
        - cross-field rules
        - application-level uniqueness checks
        - проверка статуса партнера
        """
        super().clean()

        errors: Dict[str, List[str]] = {}

        # Проверка обязательных полей
        if not self.name:
            errors.setdefault('name', []).append(
                _("Укажите наименование ПВЗ")
            )

        if not self.address:
            errors.setdefault('address', []).append(
                _("Укажите адрес ПВЗ")
            )

        if not self.work_schedule:
            errors.setdefault('work_schedule', []).append(
                _("Укажите график работы ПВЗ")
            )

        # Проверка, что партнер прошёл проверку
        # Используем локальный импорт для избежания циклических зависимостей
        if self.partner and not self.partner.validated:
            errors.setdefault('partner', []).append(
                _("Нельзя создавать/обновлять ПВЗ для партнера, который не прошёл проверку")
            )

        # Проверка уникальности наименования в рамках партнера
        if self.name and self.partner_id:
            qs = PickupPoint.objects.filter(partner_id=self.partner_id, name=self.name)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors.setdefault('name', []).append(
                    _("ПВЗ с таким наименованием уже существует для этого партнера")
                )

        if errors:
            raise ValidationError(errors)