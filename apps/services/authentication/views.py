# apps/authentication/views.py
import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from google.auth.exceptions import GoogleAuthError

# Импорты для drf-spectacular
from drf_spectacular.utils import extend_schema, OpenApiExample

from .serializers import GoogleAuthSerializer

User = get_user_model()

@extend_schema(
    summary="Аутентификация через Google",
    description=(
        "Этот эндпоинт принимает Google ID токен, валидирует его с помощью Google API, "
        "и возвращает Django API токен для дальнейшей аутентификации в системе.\n\n"
        "Если пользователя с указанным email нет в системе, создается новый пользователь. "
        "Если пользователь уже существует, возвращается существующий токен."
    ),
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'id_token': {
                    'type': 'string',
                    'description': 'Google ID токен, полученный от Google Sign-In'
                },
                'access_token': {
                    'type': 'string',
                    'description': 'Google Access токен (опционально, для дополнительных проверок)'
                }
            },
            'required': ['id_token'],
            'example': {
                'id_token': 'eyJhbGciOiJSUzI1NiIsImtpZCI6ImY5OTQxM...',
                'access_token': 'ya29.a0ARrdaM8...'
            }
        }
    },
    responses={
        200: {
            'type': 'object',
            'properties': {
                'success': {
                    'type': 'boolean',
                    'example': True,
                    'description': 'Успешность аутентификации'
                },
                'token': {
                    'type': 'string',
                    'example': '3d2e47532942e5935a3f81e34752891234567890',
                    'description': 'Django API токен для дальнейшей аутентификации'
                },
                'user': {
                    'type': 'object',
                    'properties': {
                        'id': {'type': 'integer', 'example': 1},
                        'email': {'type': 'string', 'example': 'user@example.com'},
                        'username': {'type': 'string', 'example': 'user@example.com'},
                        'first_name': {'type': 'string', 'example': 'Иван'},
                        'last_name': {'type': 'string', 'example': 'Иванов'},
                    },
                    'description': 'Информация о пользователе'
                },
                'is_new_user': {
                    'type': 'boolean',
                    'example': True,
                    'description': 'Является ли пользователь новым'
                },
                'email_verified': {
                    'type': 'boolean',
                    'example': True,
                    'description': 'Подтвержден ли email через Google'
                }
            }
        },
        400: {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'string',
                    'example': 'Неверный токен: Wrong number of segments in token',
                    'description': 'Описание ошибки'
                }
            }
        },
        401: {
            'type': 'object',
            'properties': {
                'error': {
                    'type': 'string',
                    'example': 'Ошибка аутентификации Google: ...',
                    'description': 'Описание ошибки аутентификации'
                }
            }
        }
    },
    examples=[
        OpenApiExample(
            'Успешная аутентификация нового пользователя',
            value={
                'success': True,
                'token': '3d2e47532942e5935a3f81e34752891234567890',
                'user': {
                    'id': 1,
                    'email': 'user@example.com',
                    'username': 'user@example.com',
                    'first_name': 'Иван',
                    'last_name': 'Иванов',
                },
                'is_new_user': True,
                'email_verified': True
            },
            response_only=True,
            status_codes=[200]
        ),
        OpenApiExample(
            'Неверный токен',
            value={
                'error': 'Неверный токен: Wrong number of segments in token'
            },
            response_only=True,
            status_codes=[400]
        )
    ]
)
class GoogleAuthView(APIView):
    """
    Эндпоинт для аутентификации через Google ID token из Flutter
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # 1. Валидируем входящие данные через сериализатор
        serializer = GoogleAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        id_token_str = serializer.validated_data.get('id_token')
        access_token = serializer.validated_data.get('access_token')
        
        try:
            # 2. ПОЖАЛУЙСТА, ОБРАТИТЕ ВНИМАНИЕ:
            # Для Flutter нужно использовать тот же CLIENT_ID, что и в Google Sign-In в Flutter
            # Это НЕ тот же CLIENT_ID, что для веб-приложения!
            
            # Используем уже загруженные переменные из .env
            from config.env_config import get_env_variable

            # Получаем client_id из переменных окружения
            GOOGLE_CLIENT_ID = get_env_variable('GOOGLE_MOBILE_CLIENT_ID', get_env_variable('GOOGLE_OAUTH2_CLIENT_ID', None))
            
            # 3. Проверяем токен через Google API
            idinfo = id_token.verify_oauth2_token(
                id_token_str, 
                requests.Request(),
                GOOGLE_CLIENT_ID
            )
            
            # 4. Дополнительные проверки токена
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Неверный издатель токена')
            
            # Проверяем, что токен предназначен для нашего приложения
            if idinfo['aud'] != GOOGLE_CLIENT_ID:
                raise ValueError('Неверный аудиториум токена')
            
            # Проверяем, что токен не истек
            if 'exp' in idinfo and idinfo['exp'] < time.time():
                raise ValueError('Токен истек')
            
            # 5. Получаем данные пользователя
            email = idinfo['email']
            email_verified = idinfo.get('email_verified', False)
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            
            # 6. Находим или создаем пользователя
            # Убеждаемся, что username не превышает 150 символов
            username = email[:150]  # Обрезаем, если email слишком длинный
            
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'is_active': True,
                    # Если email не подтвержден Google, возможно стоит ограничить доступ
                    # 'is_active': email_verified  
                }
            )
            
            # 7. Если пользователь существует, обновляем имя при необходимости
            if not created and (user.first_name != first_name or user.last_name != last_name):
                user.first_name = first_name
                user.last_name = last_name
                user.save(update_fields=['first_name', 'last_name'])
            
            # 8. Создаем или получаем токен DRF
            token, token_created = Token.objects.get_or_create(user=user)
            
            return Response({
                'success': True,
                'token': token.key,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                },
                'is_new_user': created,
                'email_verified': email_verified
            })
            
        except ValueError as e:
            # Токен недействителен
            return Response(
                {'error': f'Неверный токен: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except GoogleAuthError as e:
            # Ошибка аутентификации Google
            return Response(
                {'error': f'Ошибка аутентификации Google: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            # Непредвиденная ошибка
            import traceback
            import logging
            # Логируем ошибку на сервере, но не отправляем детали клиенту
            logging.error(f"Ошибка в GoogleAuthView: {str(e)}", exc_info=True)

            return Response(
                {'error': 'Внутренняя ошибка сервера'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )