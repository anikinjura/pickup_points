# apps/registry/partners/views/partner_member_viewset.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from django_filters import rest_framework as django_filters
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models import PartnerMember
from apps.registry.partners.serializers import PartnerMemberSerializer
from apps.registry.partners.permissions import (
    IsPartnerMemberOwnerOrAdmin,
    check_partner_member_management_access
)
from apps.registry.partners.filters import PartnerMemberFilter


class PartnerMemberViewSet(viewsets.ModelViewSet):
    """
    API для управления членами партнеров.
    """
    serializer_class = PartnerMemberSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerMemberOwnerOrAdmin]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PartnerMemberFilter
    search_fields = ['name', 'work_email', 'work_phone', 'employee_id']
    ordering_fields = ['name', 'created_at', 'updated_at', 'role']
    ordering = ['partner', 'name']    
    
    def get_queryset(self) -> "PartnerMemberQuerySet":  # type: ignore[override]
        user = self.request.user
        return PartnerMember.objects.for_user(user) # type: ignore[arg-type]
    
    def perform_create(self, serializer):
        partner = serializer.validated_data.get('partner')
        request_user = self.request.user

        # Проверяем права на добавление члена с использованием централизованной логики
        if not check_partner_member_management_access(request_user, partner):
            raise DRFValidationError({
                "partner": _("Нет прав для добавления членов в этого партнера")
            })

        serializer.save()
    
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Активировать члена партнера."""
        member = self.get_object()

        # Проверяем права на управление членами партнера
        if not check_partner_member_management_access(request.user, member.partner):
            raise DRFValidationError({
                "detail": _("Нет прав для активации")
            })

        member.is_active = True
        member.save()
        return Response({
            "status": "activated",
            "message": _("Член партнера активирован")
        })

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Деактивировать члена партнера."""
        member = self.get_object()

        # Проверяем права на управление членами партнера
        if not check_partner_member_management_access(request.user, member.partner):
            raise DRFValidationError({
                "detail": _("Нет прав для деактивации")
            })

        member.is_active = False
        member.save()
        return Response({
            "status": "deactivated",
            "message": _("Член партнера деактивирован")
        })