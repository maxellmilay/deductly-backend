from django.urls import path
from .views import DocumentView

urlpatterns = [
    path(
        "",
        DocumentView.as_view({"get": "list", "post": "create"}),
        name="document-list",
    ),
    path(
        "<int:pk>/",
        DocumentView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="document-detail",
    ),
]
