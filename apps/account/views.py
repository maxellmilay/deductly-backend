from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import GoogleSSOSerializer, GoogleUserInfoSerializer
from .utils.sso import verify_google_id_token
from .utils.jwt import sign_as_jwt
from .models import CustomUser


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

            if not user:
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

            payload = {"email": user.username}

            token = sign_as_jwt(payload)

            return Response({"token": token})

        except ValueError:
            return Response({"error": "Invalid Token ID"}, status=404)
