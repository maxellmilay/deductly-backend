from django.urls import path
from .views import GoogleSSOView, UserView

urlpatterns = [
    path("sso/google/", GoogleSSOView.as_view(), name="google-sso"),
    path("users/", UserView.as_view({"get": "list"}), name="users"),
]
