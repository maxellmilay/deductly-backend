from django.db import transaction
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
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
from rest_framework import status

from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from apps.camera.utils.cloudinary import upload_base64_image
import logging


class GoogleSSOView(APIView):
    """
    Handle Google SSO Authentication
    """

    GOOGLE = "google"

    @transaction.atomic
    def post(self, request, format=None):
        request_serializer = GoogleSSOSerializer(data=request.data)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=400)

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

            user_serializer = CustomUserSerializer(user)

            token = sign_as_jwt(payload)

            return Response({"token": token, "user": user_serializer.data})

        except ValueError:
            return Response({"error": "Invalid Token ID"}, status=404)


class UserView(GenericView):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    size_per_request = 1000


class AuthenticationView(APIView):
    def post(self, request, format=None):
        request_serializer = AuthenticationSerializer(data=request.data)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=400)

        request_data = request_serializer.data

        username = request_data["username"]
        password = request_data["password"]

        print(username, password)

        user = authenticate(username=username, password=password)

        if user is not None:
            payload = {"email": user.email}

            try:
                token = sign_as_jwt(payload)
            except:
                return Response({"error": "Failed JWT Signing"}, status=500)

            user_serializer = CustomUserSerializer(user)

            print(f"{user_serializer.data['username']} successfully authenticated!")
            return Response({"token": token, "user": user_serializer.data})

        else:
            print("Failed Authentication")
            return Response(
                {"error": "Failed Authentication: Incorrect Credentials"}, status=401
            )


class RegistrationView(APIView):
    def post(self, request, format=None):
        request_serializer = RegistrationSerializer(data=request.data)

        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=400)

        request_data = request_serializer.data
        email = request_data["email"]

        user = None

        try:
            user = CustomUser.objects.get(email=email)
        except Exception as e:
            print("CustomUser Query Error:", e)

        if user is None:
            username = request_data["username"]
            first_name = request_data["first_name"]
            last_name = request_data["last_name"]
            password = request_data["password"]

            user = CustomUser.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=password,
            )

            print(f"Google User {user.username} Successfully Created!")

            return Response({"username": user.username})
        else:
            print(f"User {user.username} Already Exists!")
            return Response({"error": "User already exists"}, status=409)


class CurrentUserView(APIView):
    """
    Get the current authenticated user's data
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        try:
            user = request.user
            user_serializer = CustomUserSerializer(user)

            return Response(user_serializer.data)

        except Exception as e:
            return Response({"error": "Invalid token"}, status=401)


class UserProfileUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        serializer = CustomUserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        user = request.user
        serializer = CustomUserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


logger = logging.getLogger(__name__)


@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_profile_picture(request):
    """
    Upload a profile picture to Cloudinary and update the user's profile
    """
    try:
        logger.info("Received profile picture upload request")

        # Get the image data from the request
        image_data = request.data.get("image")
        username = request.data.get("username")
        old_public_id = request.data.get("oldPublicId")

        logger.info(f"Processing upload for user: {username}")

        if not image_data:
            logger.error("No image data provided")
            return Response(
                {"success": False, "error": "No image provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not username:
            username = request.user.username
            logger.info(f"Using authenticated user's username: {username}")

        # Create a folder path with the username to keep user profile pics separate
        folder = f"user-profiles/{username}"
        logger.info(f"Using Cloudinary folder: {folder}")

        # Upload to Cloudinary
        logger.info("Uploading to Cloudinary...")
        cloudinary_result = upload_base64_image(
            image_data, filename="profile-picture", folder=folder
        )

        logger.info(f"Cloudinary upload result: {cloudinary_result}")

        if not cloudinary_result.get("success"):
            logger.error(f"Cloudinary upload failed: {cloudinary_result.get('error')}")
            return Response(
                {
                    "success": False,
                    "error": cloudinary_result.get("error", "Upload failed"),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Get the secure URL from the result
        secure_url = cloudinary_result.get("secure_url")
        public_id = cloudinary_result.get("public_id")

        logger.info(f"Image uploaded successfully. URL: {secure_url}")

        # Update the user's profile picture URL
        user = request.user
        user.profile_picture = secure_url
        user.save()
        logger.info(f"Updated user profile with new picture URL")

        # Return the result
        return Response(
            {"success": True, "secure_url": secure_url, "public_id": public_id}
        )

    except Exception as e:
        logger.error(f"Error uploading profile picture: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        return Response(
            {"success": False, "error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
