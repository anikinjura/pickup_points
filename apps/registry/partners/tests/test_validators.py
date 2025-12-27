# apps/registry/partners/tests/test_validators.py
from django.test import TestCase
from django.core.exceptions import ValidationError

from apps.registry.partners.validators.field_validators import (
    validate_inn,
    validate_ogrn,
    validate_kpp,
)


class FieldValidatorsTest(TestCase):
    def test_validate_inn_valid_10_digits(self):
        """Тест валидации 10-значного ИНН"""
        try:
            validate_inn('1234567890')
        except ValidationError:
            self.fail("Валидный 10-значный ИНН не должен вызывать ошибку")

    def test_validate_inn_valid_12_digits(self):
        """Тест валидации 12-значного ИНН"""
        try:
            validate_inn('123456789012')
        except ValidationError:
            self.fail("Валидный 12-значный ИНН не должен вызывать ошибку")

    def test_validate_inn_invalid_length(self):
        """Тест валидации ИНН неверной длины"""
        with self.assertRaises(ValidationError) as context:
            validate_inn('12345')
        
        self.assertEqual(str(context.exception), "['Некорректный ИНН']")

    def test_validate_inn_invalid_characters(self):
        """Тест валидации ИНН с нецифровыми символами"""
        with self.assertRaises(ValidationError) as context:
            validate_inn('12345abcde')
        
        self.assertEqual(str(context.exception), "['Некорректный ИНН']")

    def test_validate_inn_empty_string(self):
        """Тест валидации пустой строки ИНН"""
        try:
            validate_inn('')
            validate_inn(None)
        except ValidationError:
            self.fail("Пустой ИНН не должен вызывать ошибку")

    def test_validate_ogrn_valid_13_digits(self):
        """Тест валидации 13-значного ОГРН"""
        try:
            validate_ogrn('1234567890123')
        except ValidationError:
            self.fail("Валидный 13-значный ОГРН не должен вызывать ошибку")

    def test_validate_ogrn_valid_15_digits(self):
        """Тест валидации 15-значного ОГРН"""
        try:
            validate_ogrn('123456789012345')
        except ValidationError:
            self.fail("Валидный 15-значный ОГРН не должен вызывать ошибку")

    def test_validate_ogrn_invalid_length(self):
        """Тест валидации ОГРН неверной длины"""
        with self.assertRaises(ValidationError) as context:
            validate_ogrn('12345')
        
        self.assertEqual(str(context.exception), "['Некорректный ОГРН']")

    def test_validate_kpp_valid(self):
        """Тест валидации валидного КПП"""
        try:
            validate_kpp('123456789')
        except ValidationError:
            self.fail("Валидный КПП не должен вызывать ошибку")

    def test_validate_kpp_invalid_length(self):
        """Тест валидации КПП неверной длины"""
        with self.assertRaises(ValidationError) as context:
            validate_kpp('12345')
        
        self.assertEqual(str(context.exception), "['Некорректный КПП']")

    def test_validate_kpp_invalid_characters(self):
        """Тест валидации КПП с нецифровыми символами"""
        with self.assertRaises(ValidationError) as context:
            validate_kpp('12345abc')
        
        self.assertEqual(str(context.exception), "['Некорректный КПП']")

    def test_validate_kpp_empty_string(self):
        """Тест валидации пустой строки КПП"""
        try:
            validate_kpp('')
            validate_kpp(None)
        except ValidationError:
            self.fail("Пустой КПП не должен вызывать ошибку")