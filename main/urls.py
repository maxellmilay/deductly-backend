from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse


def home_view(request):
    return HttpResponse("Welcome to Deductly!")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.account.urls")),
    path("", home_view),
    path("extract_text/", include("apps.extract_text.urls")),
]
