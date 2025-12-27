# apps/registry/partners/filters.py
import django_filters
from django_filters import rest_framework as filters
from .models import Partner, PartnerMember

class PartnerFilter(filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    inn = django_filters.CharFilter(lookup_expr='exact')
    ogrn = django_filters.CharFilter(lookup_expr='exact')
    email = django_filters.CharFilter(lookup_expr='icontains')
    phone = django_filters.CharFilter(lookup_expr='icontains')
    validated = django_filters.BooleanFilter()
    created_after = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    
    class Meta:
        model = Partner
        fields = ['name', 'inn', 'ogrn', 'email', 'phone', 'validated']

class PartnerMemberFilter(filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    work_email = django_filters.CharFilter(lookup_expr='icontains')
    role = django_filters.ChoiceFilter(choices=PartnerMember.ROLE_CHOICES)
    is_active = django_filters.BooleanFilter()
    partner = django_filters.NumberFilter(field_name='partner_id')
    can_manage_members = django_filters.BooleanFilter()
    can_view_finance = django_filters.BooleanFilter()
    
    class Meta:
        model = PartnerMember
        fields = ['name', 'work_email', 'role', 'is_active', 'partner', 
                 'can_manage_members', 'can_view_finance']