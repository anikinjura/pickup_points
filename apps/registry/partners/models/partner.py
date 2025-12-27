from typing import Dict, List, TYPE_CHECKING
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

# RegistryModel предоставляет поле name и базовые поведенческие вещи для справочников (timestamp и т.п.).
from apps.core.models.base import RegistryModel
# Импортируем общую функцию фильтрации прав доступа
from apps.registry.partners.permissions import get_partner_filter_for_user

# локальные валидаторы (см. файл validators/field_validators.py ниже)
from apps.registry.partners.validators.field_validators import (
    validate_inn,
    validate_ogrn,
    validate_kpp,
)

if TYPE_CHECKING:
    from .partner import Partner

class PartnerQuerySet(models.QuerySet["Partner"]):
    def for_user(self, user: User) -> "PartnerQuerySet":
        """
        Возвращает набор, отфильтрованный по правам доступа:
        Использует общую логику из permissions.py
        """
        q_filter = get_partner_filter_for_user(user)
        if q_filter is None:
            return self  # Суперпользователь видит всё
        return self.filter(q_filter)

class PartnerManager(models.Manager["Partner"]):
    def get_queryset(self) -> PartnerQuerySet:
        return PartnerQuerySet(self.model, using=self._db)

    def for_user(self, user: User) -> PartnerQuerySet:
        return self.get_queryset().for_user(user)


class Partner(RegistryModel):

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_partners",
        verbose_name=_("Владелец"),
    )

    # Контактная информация (делаем поля nullable/blank, но требуем по чистке)
    email = models.EmailField(verbose_name=_("Email"), blank=True, null=True)
    phone = models.CharField(max_length=100, verbose_name=_("Телефон"), blank=True, null=True)

    # Юридические реквизиты
    legal_form = models.CharField(max_length=100, verbose_name=_("ОРФ"), blank=True, null=True)
    inn = models.CharField(max_length=12, verbose_name=_("ИНН"), validators=[validate_inn], unique=True)
    ogrn = models.CharField(max_length=15, verbose_name=_("ОГРН"), validators=[validate_ogrn], unique=True)
    kpp = models.CharField(max_length=9, verbose_name=_("КПП"), validators=[validate_kpp], blank=True, null=True)

    # Адрес
    address = models.TextField(verbose_name=_("Адрес"), blank=True, null=True)

    # Маркировка пройденной валидации (опционально; полезно для ETL/импортов)
    validated = models.BooleanField(default=False, verbose_name=_("Проверено"))
    validated_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Время проверки"))

    # Менеджер с support for_user()
    objects: PartnerManager = PartnerManager() # type: ignore

    class Meta: # pyright: ignore[reportIncompatibleVariableOverride]
        verbose_name = _("Партнёр")
        verbose_name_plural = _("Партнёры")
        ordering = ["name"]  # предполагается, что name есть в RegistryModel

        # DB-level unique constraints уже объявлены в полях (unique=True);
        # альтернативно можно задать здесь UniqueConstraint, если нужно сложное условие.

    def __str__(self) -> str:
        # RegistryModel, вероятно, уже даёт name; если нет — замените на нужное поле.
        return getattr(self, "name", f"Partner:{self.pk}")

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
 
        # 2) Cross-field: либо email, либо phone обязательно
        if not self.email and not self.phone:
            # Для одиночных ошибок можно использовать строку (а не список), но лучше использовать список для соответствия типов с ValidationError
            errors["email"] = [_("Укажите email или телефон")]

        # 3) Application-level uniqueness checks (чтобы дать понятные ошибки до вставки в БД)
        # Проверяем INN/OGRN на существование других записей (исключая self.pk при обновлении)
        if self.inn:
            qs = Partner.objects.filter(inn=self.inn)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors["inn"] = [_("Партнер с таким ИНН уже существует")]

        if self.ogrn:
            qs = Partner.objects.filter(ogrn=self.ogrn)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                errors["ogrn"] = [_("Партнер с таким ОГРН уже существует")]

        if errors:
            raise ValidationError(errors) # type: ignore

    def mark_validated(self) -> None:
        """Вспомогательная операция для отмечания записи как валидной после ручной/парсинговой проверки."""
        self.validated = True
        self.validated_at = timezone.now()
        # не сохраняем автоматически — сохраняйте в сервисе/транзакции

    # Не вызывайте full_clean() в save(). Сохранение/транзакции и перехват IntegrityError
    # обрабатывайте в сервисном слое (create/update в services/*_service.py).