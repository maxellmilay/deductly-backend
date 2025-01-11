from rest_framework.serializers import Serializer
from rest_framework import serializers


class GoogleSSOSerializer(Serializer):
    id_token = serializers.CharField(max_length=512)


class GoogleUserInfoSerializer(Serializer):
    sub = serializers.CharField(max_length=512)
    email = serializers.EmailField()
    name = serializers.CharField(max_length=512)
    picture = serializers.CharField(max_length=512)
    given_name = serializers.CharField(max_length=512)
    family_name = serializers.CharField(max_length=512)


class CustomUserSerializer(Serializer):
    first_name = serializers.CharField(max_length=512)
    last_name = serializers.CharField(max_length=512)
    username = serializers.CharField(max_length=512)


class AuthenticationSerializer(Serializer):
    username = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512)


class RegistrationSerializer(Serializer):
    username = serializers.CharField(max_length=512)
    first_name = serializers.CharField(max_length=512)
    last_name = serializers.CharField(max_length=512)
    email = serializers.CharField(max_length=512)
    password = serializers.CharField(max_length=512)
