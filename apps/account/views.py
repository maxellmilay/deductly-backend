from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import (
    GoogleSSOSerializer,
    GoogleUserInfoSerializer,
    CustomUserSerializer,
    AuthenticationSerializer,
    RegistrationSerializer,
)
from .utils.sso import verify_google_id_token
from .utils.jwt import sign_as_jwt
from .models import CustomUser
from main.utils.generic_api import GenericView


class GoogleSSOView(APIView):
    """
    Handle Google SSO Authentication
    """

    GOOGLE = "google"

    @transaction.atomic
    def post(self, request, format=None):
        request_serializer = GoogleSSOSerializer(request.data)
        request_data = request_serializer.data

        google_id_token = request_data["id_token"]

        try:
            payload = verify_google_id_token(google_id_token)

            payload_serializer = GoogleUserInfoSerializer(payload)
            payload_data = payload_serializer.data

            google_sub = payload_data["sub"]

            user = None

            try:
                user = CustomUser.objects.get(provider_sub=google_sub)
            except Exception as e:
                print("CustomUser Query Error:", e)

            if user is None:
                google_email = payload_data["email"]
                google_username = payload_data["name"]
                google_first_name = payload_data["given_name"]
                google_last_name = payload_data["family_name"]
                google_picture = payload_data["picture"]

                user = CustomUser.objects.create_user(
                    username=google_username,
                    first_name=google_first_name,
                    last_name=google_last_name,
                    email=google_email,
                    sso_provider=self.GOOGLE,
                    provider_sub=google_sub,
                    profile_picture=google_picture,
                )

                print(f"Google User {user.username} Successfully Created!")
            else:
                print(f"User {user.username} Already Exists!")

            payload = {"email": user.email}
            token = sign_as_jwt(payload)

            return Response({"token": token})

        except ValueError:
            return Response({"error": "Invalid Token ID"}, status=404)


class UserView(GenericView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    size_per_request = 1000


class AuthenticationView(APIView):
    def post(self, request, format=None):
        request_serializer = AuthenticationSerializer(request.data)
        request_data = request_serializer.data

        username = request_data["username"]
        password = request_data["password"]

        print(username, password)

        user = authenticate(username=username, password=password)

        if user is not None:
            print(f"{user.username} successfully authenticated!")

            payload = {"email": user.email}
            token = sign_as_jwt(payload)

            return Response({"token": token})

        else:
            print("Failed authentication")
            return Response({"error": "Failed Authentication"}, status=401)


class RegistrationView(APIView):
    def post(self, request, format=None):
        request_serializer = RegistrationSerializer(data=request.data)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=400)
        
        request_data = request_serializer.data

        email = request_data["email"]

        username = request_data["username"]
        first_name = request_data["first_name"]
        last_name = request_data["last_name"]
        password = request_data["password"]

        user = None

        try:
            user = CustomUser.objects.get(email=email)
        except Exception as e:
            print("CustomUser Query Error:", e)

        if user is None:
            user = CustomUser.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )

            print(f"Google User {user.username} Successfully Created!")

            return Response({"email": email})
        else:
            print(f"User {user.username} Already Exists!")
            return Response({"error": "User already exists"}, status=409)
