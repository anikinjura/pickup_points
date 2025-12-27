from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.registry.partners.models import Partner

"""
Пояснение: вы можете вызывать instance.clean() в сериализаторе, чтобы получить унифицированные сообщения, но будьте осторожны: если clean() делает DB-heavy операции — это может быть дорого. Альтернатива: в validate() выполнять только лёгкие проверки и делегировать тяжёлые проверки в сервис (bulk path).
"""

class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = "__all__"
        read_only_fields = ("owner", "validated", "validated_at") # клиенты API не смогут менять эти поля (происходит автоматически)

    def validate(self, attrs):
        """
        Валидация на уровне объекта: пытаемся вызвать model.clean() для
        унификации ошибок (работает и для админки/форм).
        Осторожно: если model.clean() делает тяжёлые DB-запросы, подумайте
        вынести такие проверки в сервис/unique_checks для bulk-путей.
        """
        # Создаём временный инстанс для валидации, комбинируя attrs и instance
        if self.instance:
            # обновление: применяем изменения на существующем экземпляре
            obj = self.instance
            for k, v in attrs.items():
                setattr(obj, k, v)
        else:
            obj = Partner(**attrs)

        try:
            # model.clean() должен поднять django.core.exceptions.ValidationError
            obj.clean()
        except DjangoValidationError as exc:
            # Преобразуем ValidationError модели в формат DRF
            if hasattr(exc, "message_dict"):
                raise serializers.ValidationError(exc.message_dict)
            else:
                raise serializers.ValidationError({"non_field_errors": exc.messages})

        return attrs
