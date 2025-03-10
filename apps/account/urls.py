from django.urls import path
from .views import GoogleSSOView, UserView, AuthenticationView, RegistrationView

urlpatterns = [
    path("sso/google/", GoogleSSOView.as_view(), name="google-sso"),
    path("users/", UserView.as_view({"get": "list"}), name="users"),
    path("authenticate/", AuthenticationView.as_view(), name="authentication"),
    path("registration/", RegistrationView.as_view(), name="registration"),
]
