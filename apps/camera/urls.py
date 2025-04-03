from django.urls import path
from .views import ImageView

urlpatterns = [
    path("", ImageView.as_view({"get": "list", "post": "create"}), name="image-list"),
    path(
        "<int:pk>/",
        ImageView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="image-detail",
    ),
]
