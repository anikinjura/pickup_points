# apps/registry/partners/serializers/partner_member_serializer.py
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _

from apps.registry.partners.models import PartnerMember


class PartnerMemberSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(
        source='partner.name', 
        read_only=True,
        label=_("Название партнера")
    )
    user_email = serializers.EmailField(
        source='user.email', 
        read_only=True, 
        allow_null=True,
        label=_("Email пользователя")
    )
    user_username = serializers.CharField(
        source='user.username', 
        read_only=True, 
        allow_null=True,
        label=_("Логин пользователя")
    )

    role_display = serializers.CharField(
        source='get_role_display',
        read_only=True,
        label=_("Роль (отображение)")
    )

    class Meta:
        model = PartnerMember
        fields = [
            'id', 'name', 'partner', 'partner_name', 'user', 'user_email', 'user_username',
            'employee_id', 'work_email', 'work_phone',
            'role', 'role_display', 'can_manage_members', 'can_view_finance', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'name': {'required': False, 'allow_blank': True}, # Поле name должно быть необязательным, так как оно может заполниться автоматически из пользователя
        }        
    
    def validate(self, attrs):
        if self.instance:
            obj = self.instance
            for k, v in attrs.items():
                setattr(obj, k, v)
        else:
            obj = PartnerMember(**attrs)
        
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
        """Проверка доступа к партнеру."""
        request = self.context.get('request')
        if request and request.user:
            from apps.registry.partners.permissions import check_partner_access
            if not check_partner_access(request.user, value):
                raise serializers.ValidationError(
                    _("Нет доступа к этому партнеру")
                )
        return value