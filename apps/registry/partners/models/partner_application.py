# apps/registry/partners/models/partner_application.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class PartnerApplicationQuerySet(models.QuerySet):
    def for_user(self, user):
        """
        Возвращает заявки, доступные для указанного пользователя.
        Использует централизованную логику из permissions.py
        """
        from apps.registry.partners.permissions import get_partner_application_filter_for_user

        filter_condition = get_partner_application_filter_for_user(user)

        if filter_condition is None:
            # Суперпользователь - без фильтрации
            return self.all()
        else:
            # Обычный пользователь - с применением фильтра
            return self.filter(filter_condition)

class PartnerApplicationManager(models.Manager):
    def get_queryset(self):
        return PartnerApplicationQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class PartnerApplication(models.Model):
    """Упрощенная заявка на создание партнера."""
    STATUS_CHOICES = [
        ('pending', _('Ожидает рассмотрения')),
        ('approved', _('Одобрена')),
        ('rejected', _('Отклонена')),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name=_('Пользователь')
    )

    # Основные данные
    company_name = models.CharField(_('Название компании'), max_length=255)
    inn = models.CharField(_('ИНН'), max_length=12, unique=True)
    ogrn = models.CharField(_('ОГРН'), max_length=15, unique=True)
    contact_email = models.EmailField(_('Контактный email'))
    contact_phone = models.CharField(_('Контактный телефон'), max_length=100)

    # Статус
    status = models.CharField(
        _('Статус'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Дополнительная информация
    processed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_applications',
        verbose_name=_('Обработана администратором')
    )
    processed_at = models.DateTimeField(
        _('Дата обработки'),
        null=True,
        blank=True
    )
    rejection_reason = models.TextField(
        _('Причина отклонения'),
        blank=True,
        null=True
    )

    # Связь с партнёром (устанавливается при одобрении заявки)
    partner = models.ForeignKey(
        'Partner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='applications',
        verbose_name=_('Созданный партнёр')
    )

    # Даты
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('Заявка партнера')
        verbose_name_plural = _('Заявки партнеров')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.get_status_display()})"

    def approve(self, admin_user):
        """Одобрить заявку"""
        if self.status != 'pending':
            raise ValueError(_('Заявка уже обработана.'))

        self.status = 'approved'
        self.processed_by = admin_user
        # processed_at автоматически обновится через auto_now

    def reject(self, admin_user, reason=''):
        """Отклонить заявку"""
        if self.status != 'pending':
            raise ValueError(_('Заявка уже обработана.'))

        self.status = 'rejected'
        self.processed_by = admin_user
        self.rejection_reason = reason
        # processed_at автоматически обновится через auto_now

    objects = PartnerApplicationManager()