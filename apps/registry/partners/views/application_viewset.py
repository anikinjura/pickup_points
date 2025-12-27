# apps/registry/partners/views/application_viewset.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.db import transaction

from apps.registry.partners.models.partner_application import PartnerApplication
from apps.registry.partners.models.partner import Partner
from apps.registry.partners.serializers.application_serializers import (
    PartnerApplicationCreateSerializer,
    PartnerApplicationSerializer,
    PartnerApplicationUserUpdateSerializer,
    PartnerApplicationAdminSerializer
)
from apps.registry.partners.services.partner_service import (
    approve_partner_application,
    reject_partner_application
)


class IsAdminOrOwner(permissions.BasePermission):
    """
    Разрешает доступ администраторам или владельцам объекта.
    """
    def has_object_permission(self, request, view, obj):
        # Администраторы могут просматривать/редактировать любые заявки
        if request.user.is_superuser:
            return True
        # Владелец может просматривать только свои заявки
        return obj.user == request.user


class PartnerApplicationViewSet(viewsets.ModelViewSet):
    """Упрощенный API для заявок."""
    serializer_class = PartnerApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Для получения и изменения заявок используются дополнительные разрешения
        """
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAuthenticated, IsAdminOrOwner]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'create':
            return PartnerApplicationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            # Администраторы могут обновлять все поля, обычные пользователи - только основные
            if self.request.user.is_staff:
                return PartnerApplicationAdminSerializer
            else:
                return PartnerApplicationUserUpdateSerializer
        else:
            return PartnerApplicationSerializer

    def get_queryset(self):
        """Пользователь видит только свои заявки, администраторы - все."""
        user = self.request.user
        return PartnerApplication.objects.for_user(user)

    def perform_create(self, serializer):
        user = self.request.user

        # Проверяем, нет ли уже активной заявки (одна активная заявка на пользователя)
        if PartnerApplication.objects.filter(
            user=user,
            status='pending'
        ).exists():
            raise ValidationError({
                'detail': _('У вас уже есть активная заявка. Дождитесь ее обработки.')
            })

        # Сохраняем заявку
        serializer.save(user=user)

    def create(self, request, *args, **kwargs):
        """Создание заявки с простым ответом."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response({
            'status': 'success',
            'message': _('Заявка успешно подана! Мы свяжемся с вами в ближайшее время.'),
            'application_id': serializer.instance.id
        }, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        """
        Обновление заявки.
        """
        application = self.get_object()

        # Проверяем, может ли пользователь обновлять заявку
        # Обычный пользователь может обновлять только заявки в статусе 'pending'
        if not request.user.is_staff:
            if application.status != 'pending':
                raise PermissionDenied(_("Нельзя изменять заявку, которая не в статусе 'pending'."))

            # Для обычных пользователей: проверяем, что они не пытаются ИЗМЕНИТЬ статус
            if 'status' in request.data and request.data['status'] != application.status:
                raise PermissionDenied(_("Обычный пользователь не может изменить статус заявки."))

        # Стандартное обновление для других полей
        serializer = self.get_serializer(application, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Обработка специфичных случаев (только для администраторов) ПОСЛЕ валидации
        # Если пользователь администратор и передал статус, обрабатываем через бизнес-логику
        if hasattr(serializer, 'validated_data') and 'status' in serializer.validated_data:
            if not request.user.is_staff:
                raise PermissionDenied(_("Только администраторы могут изменять статус заявки."))

            status_value = serializer.validated_data['status']
            if status_value == 'approved':
                # Используем сервис для одобрения
                partner, owner_member = approve_partner_application(application, request.user)

                return Response({
                    'status': 'success',
                    'message': _('Заявка одобрена. Партнер создан.'),
                    'partner_id': partner.id,
                    'partner_name': partner.name,
                    'member_id': owner_member.id
                }, status=status.HTTP_200_OK)

            elif status_value == 'rejected':
                # Получаем причину отклонения из данных
                reason = request.data.get('rejection_reason', '').strip()
                if not reason:
                    reason = 'Не указана'

                # Используем сервис для отклонения
                updated_application = reject_partner_application(application, request.user, reason)

                return Response({
                    'status': 'success',
                    'message': _('Заявка отклонена.'),
                    'reason': reason,
                    'application_id': updated_application.id
                }, status=status.HTTP_200_OK)

        # Если это не изменение статуса, просто сохраняем валидированные данные
        serializer.save()

        return Response(serializer.data)