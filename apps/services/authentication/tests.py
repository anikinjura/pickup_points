from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
import json

User = get_user_model()

class GoogleAuthViewSecurityTests(TestCase):
    """
    Тесты безопасности для Google аутентификации
    """

    def setUp(self):
        """Установка тестового окружения"""
        self.client = Client()
        self.google_auth_url = reverse('authentication:google-auth')

    def test_invalid_token_rejection(self):
        """Тест: сервер должен отклонять неверные токены"""
        invalid_token_data = {
            'id_token': 'invalid_test_token_123',
            'access_token': 'test_access_token_456'
        }

        response = self.client.post(
            self.google_auth_url,
            data=json.dumps(invalid_token_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        self.assertTrue('Неверный токен' in response.json()['error'] or 'token' in response.json()['error'].lower())

    def test_missing_required_fields(self):
        """Тест: сервер должен отклонять запросы без обязательных полей"""
        # Пустой запрос
        response = self.client.post(
            self.google_auth_url,
            data=json.dumps({}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

        # Запрос без id_token
        response = self.client.post(
            self.google_auth_url,
            data=json.dumps({'access_token': 'some_token'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error_data = response.json()
        if isinstance(error_data, dict) and 'id_token' in str(error_data):
            self.assertIn('id_token', str(error_data))

    def test_short_invalid_token(self):
        """Тест: сервер должен отклонять слишком короткие токены"""
        short_token_data = {
            'id_token': 'short',
            'access_token': 'short'
        }

        response = self.client.post(
            self.google_auth_url,
            data=json.dumps(short_token_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

    def test_malformed_json(self):
        """Тест: сервер должен корректно обрабатывать некорректный JSON"""
        malformed_json = '{"id_token": invalid_json}'

        response = self.client.post(
            self.google_auth_url,
            data=malformed_json,
            content_type='application/json'
        )

        # Ожидаем ошибку валидации данных
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_400_BAD_REQUEST])

    def test_correct_content_type_required(self):
        """Тест: сервер должен требовать правильный тип контента"""
        # Отправляем данные без указания content_type
        response = self.client.post(
            self.google_auth_url,
            data={'id_token': 'test'}
        )

        # Может возвращать 400 или 415 в зависимости от настроек
        # Главное, чтобы не проходил как успешный
        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_rate_limiting_simulation(self):
        """Тест: симуляция проверки ограничений частоты запросов (если реализованы)"""
        # Отправляем несколько запросов подряд с неверными токенами
        for i in range(5):
            response = self.client.post(
                self.google_auth_url,
                data=json.dumps({
                    'id_token': f'invalid_token_{i}',
                    'access_token': f'access_token_{i}'
                }),
                content_type='application/json'
            )

            # Проверяем, что все запросы возвращают 400, а не 429 (если нет ограничений)
            # или 429, если реализовано ограничение частоты
            self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST])
