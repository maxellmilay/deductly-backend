from django.urls import path
from .views import ImageView

urlpatterns = [
    # Process receipt endpoint
    path(
        "process_receipt/",
        ImageView.as_view({"post": "process_receipt"}),
        name="process-receipt",
    ),
    path(
        "cloudinary_images/",
        ImageView.as_view({"get": "cloudinary_images"}),
        name="cloudinary-images",
    ),
    # Other image endpoints if needed
    path("", ImageView.as_view({"get": "list", "post": "create"}), name="image-list"),
    path(
        "<int:pk>/",
        ImageView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="image-detail",
    ),
]
