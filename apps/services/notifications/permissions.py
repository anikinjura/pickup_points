from rest_framework import permissions


class IsPartnerOwnerOrAdmin(permissions.BasePermission):
    """Разрешает доступ владельцу партнёра или администратору"""
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'partner'):
            # Если у объекта есть partner, проверяем владение
            return (obj.partner.owner == request.user or 
                   request.user.is_staff or 
                   request.user.is_superuser)
        elif hasattr(obj, 'owner'):
            # Если у объекта есть owner (как у партнера)
            return obj.owner == request.user or request.user.is_staff or request.user.is_superuser
        return request.user.is_staff or request.user.is_superuser


class IsPartnerOwner(permissions.BasePermission):
    """Разрешает доступ только владельцу партнёра"""
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'partner'):
            return obj.partner.owner == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False