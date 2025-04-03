from .models import CustomUser
from rest_framework import serializers


class GoogleSSOSerializer(serializers.Serializer):
    id_token = serializers.CharField(max_length=2048)


class GoogleUserInfoSerializer(serializers.Serializer):
    sub = serializers.CharField(max_length=512)
    email = serializers.EmailField()
    name = serializers.CharField(max_length=512)
    picture = serializers.CharField(max_length=512)
    given_name = serializers.CharField(max_length=512)
    family_name = serializers.CharField(max_length=512)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = "__all__"


class AuthenticationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512)


class RegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=512)
    first_name = serializers.CharField(max_length=512)
    last_name = serializers.CharField(max_length=512)
    email = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512)
