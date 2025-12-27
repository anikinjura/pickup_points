from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
"""
Отдельный модуль для логики проверки форматов (меньше дублирования — используются и в моделях, и при необходимости в сериализаторах)
Замечание: для INN/OGRN можно добавить проверку контрольной суммы — лучше держать её в этой функции, чтобы фронт/сериализатор/модель использовали одну логику.
"""

def validate_inn(value: str) -> None:
    """
    Простая структурная проверка INN: длина и цифровые символы.
    Для контрольной суммы можно расширить логику.
    """
    if value in (None, ""):
        return
    if not isinstance(value, str) or not value.isdigit() or len(value) not in (10, 12):
        raise ValidationError(_("Некорректный ИНН"))


def validate_ogrn(value: str) -> None:
    if value in (None, ""):
        return
    if not isinstance(value, str) or not value.isdigit() or len(value) not in (13, 15):
        raise ValidationError(_("Некорректный ОГРН"))


def validate_kpp(value: str) -> None:
    if value in (None, ""):
        return
    # KPP — 9 digits (пример простая проверка)
    if not isinstance(value, str) or not value.isdigit() or len(value) != 9:
        raise ValidationError(_("Некорректный КПП"))
