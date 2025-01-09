from django.db import transaction
from rest_framework.views import APIView
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
            google_email = payload_data["email"]
            google_name = payload_data.get("name")
            google_picture = payload_data.get("picture")

            user = CustomUser.objects.get(provider_sub=google_sub)

            if not user:
                user = CustomUser.objects.get(email=google_email)
                if not user:
                    user = CustomUser.objects.create_user(
                        username=google_name,
                        email=google_email,
                        sso_provider=self.GOOGLE,
                        provider_sub=google_sub,
                        profile_picture=google_picture,
                    )

            payload = {"email": google_email}

            token = sign_as_jwt(payload)

            return {"token": token}

        except ValueError:
            return {"error": "Invalid Token ID"}, 401
