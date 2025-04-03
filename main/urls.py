from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/account/", include("apps.account.urls")),
    path("api/v1/camera/", include("apps.camera.urls")),
    path("api/v1/document/", include("apps.document.urls")),
    path("api/v1/receipt/", include("apps.receipt.urls")),
    path("api/v1/report/", include("apps.report.urls")),
]
