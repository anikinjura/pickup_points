# apps/authentication/serializers.py
from rest_framework import serializers

class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)
    access_token = serializers.CharField(required=False)