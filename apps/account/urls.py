from django.urls import path
from .views import UserProfileUpdateView
from .views import (
    GoogleSSOView,
    UserView,
    AuthenticationView,
    RegistrationView,
    CurrentUserView,
)

urlpatterns = [
    path("sso/google/", GoogleSSOView.as_view(), name="google-sso"),
    path("users/", UserView.as_view({"get": "list"}), name="users"),
    path("authenticate/", AuthenticationView.as_view(), name="authentication"),
    path("registration/", RegistrationView.as_view(), name="registration"),
    path("me/", CurrentUserView.as_view(), name="current-user"),
    path("me/update/", UserProfileUpdateView.as_view(), name="user-profile-update"),
]
