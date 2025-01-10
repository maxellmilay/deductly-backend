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
