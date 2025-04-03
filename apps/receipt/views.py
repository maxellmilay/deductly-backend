from main.utils.generic_api import GenericView
from .serializers import ReceiptSerializer, VendorSerializer, ReceiptItemSerializer
from .models import Receipt, Vendor, ReceiptItem


class ReceiptView(GenericView):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "receipt"


class VendorView(GenericView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "vendor"


class ReceiptItemView(GenericView):
    queryset = ReceiptItem.objects.all()
    serializer_class = ReceiptItemSerializer
    # permission_classes = [IsAuthenticated]
    cache_key_prefix = "receipt_item"
