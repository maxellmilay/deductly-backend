from django.urls import path
from .views import GoogleSSOView

urlpatterns = [path("sso/google/", GoogleSSOView.as_view(), name="google-sso")]
