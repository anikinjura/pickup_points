# config/urls.py
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.http import JsonResponse
from apps.services.authentication.views import GoogleAuthView
from config.admin import admin_site

def profile_stub(request):
    """Заглушка для /accounts/profile/ - возвращает JSON для бэкенда API."""
    return JsonResponse({
        'backend': 'Partner Registry API',
        'message': 'Это бэкенд для Flutter приложения',
        'authenticated': request.user.is_authenticated,
        'user_email': request.user.email if request.user.is_authenticated else None,
        'next_steps': {
            'check_user_status': '/api/user-status/',
            'api_documentation': '/api/docs/',
            'all_endpoints': '/api/'
        },
        'note': 'Для работы с API используйте токен аутентификации. После социальной авторизации проверьте /api/user-status/'
    })

urlpatterns = [
    path("admin/", admin_site.urls),

    # API приложения partners
    path('api/', include('apps.registry.partners.urls')),

    # REST Auth (dj-rest-auth) для API
    path('api/auth/', include('dj_rest_auth.urls')),

    # Google OAuth для Flutter
    path('api/auth/google/', include('apps.services.authentication.urls')),


    # Документация API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]