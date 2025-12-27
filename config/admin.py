from django.contrib.admin import AdminSite
from django.contrib.auth.views import LoginView
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.http import HttpResponseRedirect


class CustomLoginView(LoginView):
    """
    Кастомное представление для входа в админку без использования фреймворка sites
    """
    template_name = 'admin/login.html'

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Не вызываем get_current_site, чтобы избежать зависимости от фреймворка sites
        context.update({
            'title': 'Вход в админку',
            'app_path': self.request.get_full_path(),
            # Добавляем необходимые переменные, которые обычно предоставляет фреймворк sites
            'site': {'name': 'Партнерские Точки Выдачи'},
            'site_name': 'ППВ',
        })
        return context


class CustomAdminSite(AdminSite):
    """
    Кастомная админка без зависимости от фреймворка sites
    """
    login_view = 'admin_login'  # Указываем имя URL-адреса для кастомного входа

    def each_context(self, request):
        context = super().each_context(request)
        # Убираем использование get_current_site
        context.update({
            'site_title': self.site_title,
            'site_header': self.site_header,
            'has_permission': request.user.is_authenticated,
            # Добавляем переменные, которые обычно предоставляет фреймворк sites
            'site_name': 'ППВ',
        })
        return context


# Создаем экземпляр кастомной админки
admin_site = CustomAdminSite()
admin_site.site_header = 'Админка Партнерских Точек Выдачи'
admin_site.site_title = 'Админка ППВ'
admin_site.index_title = 'Добро пожаловать в админку'