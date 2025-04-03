from jwt import ExpiredSignatureError, InvalidTokenError
from django.http import JsonResponse
from django.contrib.auth.models import AnonymousUser
from apps.account.utils.jwt import verify_jwt_token


class UserProxy:
    """
    A lightweight proxy object to represent authenticated users.
    """

    def __init__(self, email, payload):
        self.email = email
        self.payload = payload
        self.is_active = True  # Set required attributes

    def __str__(self):
        return self.email


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.excluded_paths = [
            "/api/v1/sso/google/",
            "/api/v1/authenticate/",
            "/api/v1/registration/",
        ]

    def __call__(self, request):
        if request.path in self.excluded_paths or request.path.startswith("/admin/"):
            return self.get_response(request)

        # Process JWT authentication for other paths
        auth_header = request.headers.get("Authorization", None)
        email_header = request.headers.get("X-User-Email", None)

        if auth_header:
            try:
                token = auth_header.split()[1].strip('"')
                payload = verify_jwt_token(token, email_header)
                # Assign a lightweight proxy user object
                request.user = UserProxy(email_header, payload)
            except ExpiredSignatureError:
                return JsonResponse({"error": "Token has expired"}, status=401)
            except InvalidTokenError:
                return JsonResponse({"error": "Invalid token"}, status=401)
        else:
            # Assign AnonymousUser for unauthenticated requests
            request.user = AnonymousUser()

        return self.get_response(request)
