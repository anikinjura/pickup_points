# apps/registry/partners/views/auth_views.py
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models.partner import Partner
from apps.registry.partners.models.partner_member import PartnerMember
from apps.registry.partners.models.partner_application import PartnerApplication
from apps.registry.partners.serializers.application_serializers import UserStatusSerializer


class UserStatusView(GenericAPIView):
    """
    Проверка статуса пользователя после входа.
    Использует централизованную логику фильтрации через .for_user()
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserStatusSerializer

    def get(self, request):
        user = request.user

        # Используем централизованную логику фильтрации
        user_partners = Partner.objects.for_user(user)
        user_memberships = PartnerMember.objects.for_user(user)
        user_applications = PartnerApplication.objects.for_user(user)

        # Проверяем наличие активной заявки у пользователя
        has_pending_application = user_applications.filter(status='pending').exists()

        # Собираем всех партнеров пользователя (владения + членства)
        all_partners = []

        # Добавляем партнёров, которыми пользователь владеет
        for partner in user_partners:
            all_partners.append({
                'id': partner.id,
                'name': partner.name,
                'inn': partner.inn,
                'role': 'owner',
                'created_at': partner.created_at
            })

        # Добавляем партнёры, где пользователь является членом
        for membership in user_memberships:
            # Проверяем, не добавлен ли уже этот партнёр как владение
            if not any(p['id'] == membership.partner.id for p in all_partners):
                all_partners.append({
                    'id': membership.partner.id,
                    'name': membership.partner.name,
                    'inn': membership.partner.inn,
                    'role': membership.get_role_display(),  # Используем отображаемое имя роли
                    'created_at': membership.created_at,
                    'is_active': membership.is_active  # Добавим статус активности
                })

        # Формируем сообщение
        has_active_memberships = user_memberships.filter(is_active=True).exists()
        has_any_memberships = user_memberships.exists()

        if user_partners.exists() or has_any_memberships:
            if len(all_partners) == 1:
                partner = all_partners[0]
                role = partner.get('role', 'member')
                # Показываем, что членство неактивно, если это так
                if not partner.get('is_active', True):
                    role = f"{role} (неактивен)"
                message = _('Добро пожаловать! Вы вошли как {role} партнера "{name}"').format(
                    role=role,
                    name=partner['name']
                )
            else:
                message = _('Добро пожаловать! У вас есть доступ к {count} партнерам').format(
                    count=len(all_partners)
                )
        else:
            message = _('Добро пожаловать! У вас еще нет партнера. Вы можете подать заявку на создание.')

        # Формируем ответ
        data = {
            'has_partners': user_partners.exists(),
            'has_memberships': has_any_memberships,  # Любой статус членства
            'has_memberships_active': has_active_memberships,  # Только активные
            'has_pending_application': has_pending_application,
            'message': message,
            'partners': all_partners if all_partners else None,
        }

        serializer = self.get_serializer()
        result = serializer.to_representation(data)
        return Response(result)