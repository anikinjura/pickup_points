# apps/authentication/urls.py
from django.urls import path
from .views import GoogleAuthView

app_name = 'authentication'

urlpatterns = [
    path('google/', GoogleAuthView.as_view(), name='google-auth'),
]