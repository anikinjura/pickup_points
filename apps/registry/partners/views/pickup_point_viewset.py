# apps/registry/partners/views/pickup_point_viewset.py
from rest_framework import viewsets, permissions, filters, status
from django_filters import rest_framework as django_filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models import PickupPoint
from apps.registry.partners.serializers import PickupPointSerializer
from apps.registry.partners.permissions import (
    IsPickupPointOwnerOrAdmin,
    check_pickup_point_access,
    check_pickup_point_crud_access
)
from apps.registry.partners.filters import PickupPointFilter


class PickupPointViewSet(viewsets.ModelViewSet):
    """
    API для управления пунктами выдачи заказов (ПВЗ).
    """
    serializer_class = PickupPointSerializer
    permission_classes = [permissions.IsAuthenticated, IsPickupPointOwnerOrAdmin]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PickupPointFilter
    search_fields = ['name', 'address']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['partner', 'name']

    def get_queryset(self) -> "PickupPointQuerySet":  # type: ignore[override]
        user = self.request.user
        return PickupPoint.objects.for_user(user)  # type: ignore[arg-type]

    def get_permissions(self):
        """
        Для получения ПВЗ используются более мягкие разрешения
        """
        if self.action in ['list', 'retrieve']:
            # Для просмотра разрешаем доступ тем, кто имеет доступ к ПВЗ
            permission_classes = [permissions.IsAuthenticated]
        else:
            # Для CRUD операций требуем более строгих разрешений
            permission_classes = [permissions.IsAuthenticated, IsPickupPointOwnerOrAdmin]
        return [permission() for permission in permission_classes]

    def perform_create(self, serializer):
        partner = serializer.validated_data.get('partner')
        request_user = self.request.user

        # Проверяем права и статус партнера через централизованную логику
        from apps.registry.partners.permissions import validate_partner_pickup_point_access
        if not validate_partner_pickup_point_access(request_user, partner):
            raise DRFValidationError({
                "partner": _("Нет прав для создания ПВЗ для этого партнера или партнер не прошёл проверку")
            })

        serializer.save()

    def perform_update(self, serializer):
        # Проверяем права на обновление
        pickup_point = self.get_object()
        request_user = self.request.user

        if not check_pickup_point_crud_access(request_user, pickup_point):
            raise DRFValidationError({
                "detail": _("Нет прав для обновления этого ПВЗ")
            })

        # Проверяем права и статус партнера через централизованную логику
        partner = serializer.validated_data.get('partner', pickup_point.partner)
        from apps.registry.partners.permissions import validate_partner_pickup_point_access
        if not validate_partner_pickup_point_access(request_user, partner):
            raise DRFValidationError({
                "partner": _("Нет прав для обновления ПВЗ для этого партнера или партнер не прошёл проверку")
            })

        serializer.save()

    def perform_destroy(self, instance):
        # Проверяем права на удаление
        request_user = self.request.user

        if not check_pickup_point_crud_access(request_user, instance):
            raise DRFValidationError({
                "detail": _("Нет прав для удаления этого ПВЗ")
            })

        instance.delete()

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить только активные ПВЗ."""
        user = request.user
        queryset = PickupPoint.objects.for_user(user).active()

        # Применяем фильтрацию
        filtered_queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Активировать ПВЗ."""
        pickup_point = self.get_object()

        if not check_pickup_point_crud_access(request.user, pickup_point):
            return Response(
                {"detail": _("Нет прав для активации")},
                status=status.HTTP_403_FORBIDDEN
            )

        pickup_point.is_active = True
        pickup_point.save()
        serializer = self.get_serializer(pickup_point)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Деактивировать ПВЗ."""
        pickup_point = self.get_object()

        if not check_pickup_point_crud_access(request.user, pickup_point):
            return Response(
                {"detail": _("Нет прав для деактивации")},
                status=status.HTTP_403_FORBIDDEN
            )

        pickup_point.is_active = False
        pickup_point.save()
        serializer = self.get_serializer(pickup_point)
        return Response(serializer.data)