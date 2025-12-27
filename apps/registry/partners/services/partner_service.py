from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from typing import cast, Optional
from apps.registry.partners.models import Partner, PartnerMember, PartnerApplication
from apps.registry.partners.serializers import PartnerSerializer, PartnerMemberSerializer

"""
Почему: даже при application-level unique проверки возможны гонки. Поэтому на уровне сервиса оборачиваем сохранение в транзакцию и ловим IntegrityError, переводя в ValidationError (чтобы DRF сериализатор/вью получили дружелюбную ошибку).
"""

def create_partner(data: dict, owner) -> Partner:
    """Создание партнёра"""
    serializer = PartnerSerializer(data=data)
    if not serializer.is_valid():
        raise ValidationError(serializer.errors)

    try:
        with transaction.atomic():
            # задаём owner явным образом (если сериализатор не делает этого), явно указываем тип с помощью cast
            instance = cast(Partner, serializer.save(owner=owner)) # было instance: Partner = serializer.save(owner=owner)
    except IntegrityError as exc:
        # распарсите exc для определения поля (если возможно) или верните общий конфликт, например:
        if "unique" in str(exc).lower():
            if "inn" in str(exc).lower():
                raise ValidationError({"inn": "partner_with_this_inn_already_exists"})
            elif "ogrn" in str(exc).lower():
                raise ValidationError({"ogrn": "partner_with_this_ogrn_already_exists"})
        raise ValidationError({"detail": "database_integrity_error"})
    return instance

def create_partner_from_application(application: PartnerApplication) -> Partner:
    """
    Создание партнёра из данных заявки

    Args:
        application: объект PartnerApplication с данными для создания партнёра

    Returns:
        Partner: созданный партнёр
    """
    partner_data = {
        'name': application.company_name,
        'inn': application.inn,
        'ogrn': application.ogrn,
        'email': application.contact_email,  # Map contact_email -> email
        'phone': application.contact_phone,  # Map contact_phone -> phone
    }

    return create_partner(partner_data, application.user)

def create_initial_partner_member(partner: Partner, user, application: PartnerApplication) -> PartnerMember:
    """
    Создание начального членства (владельца) для партнёра

    Args:
        partner: объект созданного партнёра
        user: пользователь, который станет владельцем
        application: заявка, на основе которой создаётся членство

    Returns:
        PartnerMember: созданный владелец партнёра
    """
    member_data = {
        'partner': partner.id,  # Передаём ID, а не объект
        'user': user.id,        # Передаём ID, а не объект
        'role': 'director',     # Используем 'director' для владельца
        'name': user.get_full_name() or user.username,
        'work_email': application.contact_email,
        'work_phone': application.contact_phone,
    }

    serializer = PartnerMemberSerializer(data=member_data)
    if not serializer.is_valid():
        raise ValidationError(serializer.errors)

    try:
        with transaction.atomic():
            member = serializer.save()
            # Вызываем full_clean() для применения логики из clean() модели
            member.full_clean()
            # Сохраняем изменения, внесённые clean()
            member.save(update_fields=['can_manage_members', 'can_view_finance'])
            return member
    except IntegrityError as exc:
        raise ValidationError({"detail": "database_integrity_error"})

def update_application_status(
    application: PartnerApplication,
    status: str,
    processed_by,
    rejection_reason: Optional[str] = None
) -> PartnerApplication:
    """
    Обновление статуса заявки

    Args:
        application: объект PartnerApplication
        status: новый статус ('approved', 'rejected', 'pending')
        processed_by: пользователь, обработавший заявку
        rejection_reason: причина отклонения (для статуса 'rejected')

    Returns:
        PartnerApplication: обновлённая заявка
    """
    application.status = status
    application.processed_at = timezone.now()
    application.processed_by = processed_by
    if rejection_reason:
        application.rejection_reason = rejection_reason

    application.save(update_fields=['status', 'processed_at', 'processed_by', 'rejection_reason'])
    return application

def approve_partner_application(application: PartnerApplication, admin_user) -> tuple[Partner, PartnerMember]:
    """
    Одобрение заявки на создание партнёра

    Args:
        application: объект PartnerApplication со статусом 'pending'
        admin_user: пользователь-администратор, одобряющий заявку

    Returns:
        tuple[Partner, PartnerMember]: созданный партнёр и его владелец
    """
    with transaction.atomic():
        if application.status != 'pending':
            raise ValidationError({"status": "Application must be in pending status"})

        # 1. Создать партнёра из заявки
        partner = create_partner_from_application(application)

        # 2. Создать начального владельца
        owner_member = create_initial_partner_member(partner, application.user, application)

        # 3. Обновить статус заявки
        update_application_status(application, 'approved', admin_user)

        # 4. Связать заявку с партнёром
        application.partner = partner
        application.save(update_fields=['partner'])

        return partner, owner_member

def reject_partner_application(application: PartnerApplication, admin_user, reason: str) -> PartnerApplication:
    """
    Отклонение заявки на создание партнёра

    Args:
        application: объект PartnerApplication со статусом 'pending'
        admin_user: пользователь-администратор, отклоняющий заявку
        reason: причина отклонения

    Returns:
        PartnerApplication: обновлённая заявка
    """
    with transaction.atomic():
        if application.status != 'pending':
            raise ValidationError({"status": "Application must be in pending status"})

        # Обновить статус и причину отклонения
        updated_application = update_application_status(application, 'rejected', admin_user, reason)
        return updated_application
