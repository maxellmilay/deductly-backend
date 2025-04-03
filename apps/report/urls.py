from django.urls import path
from .views import ReportView

urlpatterns = [
    path("", ReportView.as_view({"get": "list", "post": "create"}), name="report-list"),
    path(
        "<int:pk>/",
        ReportView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="report-detail",
    ),
]
