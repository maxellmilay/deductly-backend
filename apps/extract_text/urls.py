# apps/extract_text/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("upload/", views.upload_receipt, name="upload_receipt"),
    path("download-csv/", views.download_csv, name="download_csv"),
]
