# apps/registry/partners/serializers/pickup_point_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models import PickupPoint


class PickupPointSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(
        source='partner.name',
        read_only=True,
        label=_("Название партнера")
    )

    class Meta:
        model = PickupPoint
        fields = [
            'id', 'name', 'partner', 'partner_name', 'address', 'location_details',
            'work_schedule', 'phone', 'email', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance:
            obj = self.instance
            for k, v in attrs.items():
                setattr(obj, k, v)
        else:
            obj = PickupPoint(**attrs)

        try:
            obj.clean()
        except DjangoValidationError as exc:
            if hasattr(exc, 'message_dict'):
                raise serializers.ValidationError(exc.message_dict)
            else:
                raise serializers.ValidationError({
                    "non_field_errors": exc.messages
                })

        return attrs

    def validate_partner(self, value):
        """Проверка доступа к партнеру и его статуса проверки."""
        request = self.context.get('request')
        if request and request.user:
            from apps.registry.partners.permissions import validate_partner_pickup_point_access
            if not validate_partner_pickup_point_access(request.user, value):
                raise serializers.ValidationError(
                    _("Нет доступа к этому партнеру или партнер не прошёл проверку")
                )
        return value