# apps/extract_text/urls.py

from django.urls import path
from .views import upload_receipt

urlpatterns = [
    path("upload/", upload_receipt, name="upload_receipt"),
]
