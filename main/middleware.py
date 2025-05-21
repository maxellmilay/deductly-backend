from jwt import ExpiredSignatureError, InvalidTokenError
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from apps.account.utils.jwt import verify_jwt_token
from apps.account.models import CustomUser
import logging
import re

logger = logging.getLogger(__name__)


class DisableCSRFMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if re.match(r"^/api/.*$", request.path):
            setattr(request, "_dont_enforce_csrf_checks", True)
        return self.get_response(request)


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = [
            "/api/v1/account/sso/google/",
            "/api/v1/account/authenticate/",
            "/api/v1/account/registration/",
        ]

    def __call__(self, request):
        if request.path in self.excluded_paths or request.path.startswith("/admin/"):
            return self.get_response(request)

        # Process JWT authentication for other paths
        auth_header = request.headers.get("Authorization", None)
        email_header = request.headers.get("X-User-Email", None)

        logger.info(f"TESTING AUTH HEADER: {auth_header}")
        logger.info(f"TESTING EMAIL HEADER: {email_header}")

        if auth_header:
            try:
                token = auth_header.split()[1].strip('"')
                payload = verify_jwt_token(token, email_header)
                logger.info(f"TESTING PAYLOAD: {payload}")
                # Assign a lightweight proxy user object
                email = payload.get("email")
                request.user = CustomUser.objects.get(email=email)
                logger.info(f"TESTING REQUEST USER: {request.user}")
            except ExpiredSignatureError:
                return JsonResponse({"error": "Token has expired"}, status=401)
            except InvalidTokenError:
                return JsonResponse({"error": "Invalid token"}, status=401)
        else:
            # Assign AnonymousUser for unauthenticated requests
            request.user = AnonymousUser()

        return self.get_response(request)
