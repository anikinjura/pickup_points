# apps/registry/partners/views/partner_viewset.py
from rest_framework import viewsets, permissions, filters, status
from django_filters import rest_framework as django_filters
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema

from apps.registry.partners.models import Partner, PartnerMember
from apps.registry.partners.serializers.partner_serializer import PartnerSerializer
from apps.registry.partners.serializers.partner_member_serializer import PartnerMemberSerializer
from apps.registry.partners.permissions import IsOwnerOrAdmin, check_partner_access, check_partner_member_access
from apps.registry.partners.filters import PartnerFilter
from apps.services.notifications.models import TelegramConfig
from apps.services.notifications.serializers.telegram_config_serializer import PartnerTelegramConfigSerializer
from apps.services.notifications.services.notification_service import NotificationService
from apps.services.notifications.tasks.notification_tasks import (
    validate_telegram_config_task,
    send_notification_from_partner_task
)
from apps.registry.partners.serializers.notification_serializers import CreateNotificationSerializer, SendPartnerNotificationSerializer
from apps.services.notifications.serializers.notification_serializer import NotificationSerializer

class PartnerViewSet(viewsets.ModelViewSet):
    """
    CRUD API для Partner.
    - queryset фильтруется по владельцу в get_queryset (использует Partner.objects.for_user)
    - object-level permissions обеспечиваются IsOwnerOrAdmin
    - на create/update перехватываем IntegrityError и возвращаем DRF ValidationError
    """
    serializer_class = PartnerSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PartnerFilter
    search_fields = ['name', 'inn', 'ogrn', 'email', 'phone']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']        

    def get_queryset(self) -> "PartnerQuerySet":  # type: ignore[override]
        # PartnerManager должен реализовать .for_user(user)
        user = self.request.user
        return Partner.objects.for_user(user) # type: ignore[arg-type]

    def perform_create(self, serializer):
        # Создаём объект в транзакции и ловим IntegrityError (гонки по unique)
        try:
            with transaction.atomic():
                # явно привязываем owner текущему user
                serializer.save(owner=self.request.user)
        except IntegrityError as exc:
            # Можно попытаться распарсить exc для поля; возвращаем дружелюбную ошибку
            raise DRFValidationError({"non_field_errors": ["database_integrity_error"]})

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise DRFValidationError({"non_field_errors": ["database_integrity_error"]})


    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Статистика по партнерам."""
        user = request.user
        # Используем централизованную логику фильтрации
        queryset = Partner.objects.for_user(user)

        total_partners = queryset.count()
        validated_partners = queryset.filter(validated=True).count()
        partners_with_members = queryset.annotate(
            member_count=Count('members')
        ).filter(member_count__gt=0).count()

        # Статистика по членам
        total_members = PartnerMember.objects.filter(
            partner__in=queryset
        ).count()
        active_members = PartnerMember.objects.filter(
            partner__in=queryset,
            is_active=True
        ).count()

        return Response({
            'total_partners': total_partners,
            'validated_partners': validated_partners,
            'partners_with_members': partners_with_members,
            'total_members': total_members,
            'active_members': active_members,
        })
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Получить всех членов конкретного партнера."""
        partner = self.get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Для получения членов конкретного партнера используем только членов этого партнера
        # и применяем фильтрацию по правам доступа
        all_members = partner.members.all()

        # Фильтруем только те членства, к которым пользователь имеет доступ
        accessible_members = []
        for member in all_members:
            if check_partner_member_access(request.user, member):
                accessible_members.append(member)

        page = self.paginate_queryset(accessible_members)
        if page is not None:
            serializer = PartnerMemberSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PartnerMemberSerializer(accessible_members, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        request=PartnerTelegramConfigSerializer,
        responses={200: PartnerTelegramConfigSerializer, 400: {'type': 'object'}},
        description="Установка/обновление конфигурации Telegram для конкретного партнёра"
    )
    @action(detail=True, methods=['post'])
    def set_telegram_config(self, request, pk=None):
        """Установка/обновление конфигурации Telegram для конкретного партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            config = TelegramConfig.objects.get(partner=partner)
            serializer = PartnerTelegramConfigSerializer(config, data=request.data, partial=True)
        except TelegramConfig.DoesNotExist:
            serializer = PartnerTelegramConfigSerializer(data=request.data)

        if serializer.is_valid():
            if not hasattr(serializer.instance, 'partner'):
                # Новый объект - устанавливаем партнёра
                config = serializer.save(partner=partner)
            else:
                # Существующий объект - просто сохраняем
                config = serializer.save()

            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        request=None,
        responses={200: PartnerTelegramConfigSerializer, 404: {'type': 'object'}},
        description="Получение конфигурации Telegram для конкретного партнёра"
    )
    @action(detail=True, methods=['get'])
    def get_telegram_config(self, request, pk=None):
        """Получение конфигурации Telegram для конкретного партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            config = TelegramConfig.objects.get(partner=partner)
            serializer = PartnerTelegramConfigSerializer(config)
            return Response(serializer.data)
        except TelegramConfig.DoesNotExist:
            return Response({}, status=status.HTTP_200_OK)

    @extend_schema(
        request=None,
        responses={200: {'type': 'object'}, 404: {'type': 'object'}},
        description="Валидация конфигурации Telegram для конкретного партнёра"
    )
    @action(detail=True, methods=['post'])
    def validate_telegram_config(self, request, pk=None):
        """Валидация конфигурации Telegram для конкретного партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            config = TelegramConfig.objects.get(partner=partner)
            task = validate_telegram_config_task.delay(config.id)

            return Response({
                'message': 'Валидация конфигурации поставлена в очередь',
                'task_id': task.id,
                'config_id': config.id
            })
        except TelegramConfig.DoesNotExist:
            return Response(
                {'error': 'Telegram конфигурация не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )

    @extend_schema(
        request=SendPartnerNotificationSerializer,
        responses={200: {'type': 'object'}, 400: {'type': 'object'}},
        description="Отправка уведомления от имени партнёра (требует настроенную конфигурацию партнёра)"
    )
    @action(detail=True, methods=['post'])
    def send_partner_notification(self, request, pk=None):
        """Отправка уведомления от имени партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        message = request.data.get('message', '')
        if not message:
            return Response(
                {'error': 'Требуется сообщение'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, что у партнёра есть активная конфигурация
        try:
            config = TelegramConfig.objects.get(partner=partner, is_active=True)
        except TelegramConfig.DoesNotExist:
            return Response(
                {'error': 'Активная Telegram конфигурация не найдена'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Асинхронная отправка от имени партнёра
        task = send_notification_from_partner_task.delay(partner.id, message)

        return Response({
            'message': 'Уведомление от имени партнёра поставлено в очередь',
            'task_id': task.id
        })

    @extend_schema(
        request=None,
        responses={200: {'type': 'array', 'items': {'$ref': '#/components/schemas/NotificationSerializer'}},
                   404: {'type': 'object'}},
        description="Получение уведомлений для конкретного партнёра"
    )
    @action(detail=True, methods=['get'])
    def notifications(self, request, pk=None):
        """Получение уведомлений для конкретного партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        from apps.services.notifications.models import Notification
        notifications = Notification.objects.filter(partner=partner).order_by('-created_at')
        from apps.services.notifications.serializers.notification_serializer import NotificationSerializer
        serializer = NotificationSerializer(notifications, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        request=CreateNotificationSerializer,
        responses={201: {'$ref': '#/components/schemas/NotificationSerializer'}, 400: {'type': 'object'}},
        description="Создание уведомления для конкретного партнёра"
    )
    @action(detail=True, methods=['post'])
    def create_notification(self, request, pk=None):
        """Создание уведомления для конкретного партнёра"""
        partner = self.get_object()  # Это уже проверяет права доступа через get_object()

        # Проверяем права доступа с использованием централизованной логики
        if not check_partner_access(request.user, partner):
            return Response(
                {"detail": "У вас нет доступа к этому партнеру"},
                status=status.HTTP_403_FORBIDDEN
            )

        from apps.services.notifications.models import Notification

        serializer = CreateNotificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Создаём уведомление с partner
            notification = serializer.save(partner=partner)
            # Возвращаем полное представление уведомления
            response_serializer = NotificationSerializer(notification, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
