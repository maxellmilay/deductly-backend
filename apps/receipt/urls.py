from django.urls import path
from .views import ReceiptView, VendorView, ReceiptItemView

urlpatterns = [
    path(
        "", ReceiptView.as_view({"get": "list", "post": "create"}), name="receipt-list"
    ),
    path(
        "<int:pk>/",
        ReceiptView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="receipt-detail",
    ),
    path(
        "vendor/",
        VendorView.as_view({"get": "list", "post": "create"}),
        name="vendor-list",
    ),
    path(
        "vendor/<int:pk>/",
        VendorView.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="vendor-detail",
    ),
    path(
        "receipt-item/",
        ReceiptItemView.as_view({"get": "list", "post": "create"}),
        name="receipt-item-list",
    ),
    path(
        "receipt-item/<int:pk>/",
        ReceiptItemView.as_view(
            {"get": "retrieve", "put": "update", "delete": "destroy"}
        ),
        name="receipt-item-detail",
    ),
]
