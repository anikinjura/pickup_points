# apps/registry/partners/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    PartnerViewSet,
    PartnerMemberViewSet,
    PartnerApplicationViewSet,
    PickupPointViewSet,
    UserStatusView
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

router = DefaultRouter()
router.register(r'partners', PartnerViewSet, basename='partner')
router.register(r'partner-members', PartnerMemberViewSet, basename='partner-member')
router.register(r'applications', PartnerApplicationViewSet, basename='application')
router.register(r'pickup-points', PickupPointViewSet, basename='pickup-point')

@extend_schema(
    operation_id='api_root',
    description='Корневой эндпоинт API, возвращает список доступных эндпоинтов',
    responses={200: {'type': 'object', 'additionalProperties': True}},
)
@api_view(['GET'])
def api_root(request):
    return Response({
        'partners': request.build_absolute_uri('partners/'),
        'partner-members': request.build_absolute_uri('partner-members/'),
        'applications': request.build_absolute_uri('applications/'),
        'pickup-points': request.build_absolute_uri('pickup-points/'),
        'user-status': request.build_absolute_uri('user-status/'),
        'auth': {
            'login': request.build_absolute_uri('../auth/login/'),
            'logout': request.build_absolute_uri('../auth/logout/'),
            'user': request.build_absolute_uri('../auth/user/'),
            'social-login': {
                'google': request.build_absolute_uri('../../accounts/google/login/'),
            }
        }
    })

urlpatterns = [
    path('', api_root, name='api-root'),
    path('user-status/', UserStatusView.as_view(), name='user-status'),
] + router.urls