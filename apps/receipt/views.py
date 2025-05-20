from main.utils.generic_api import GenericView
from .serializers import ReceiptSerializer, VendorSerializer, ReceiptItemSerializer
from .models import Receipt, Vendor, ReceiptItem
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q


class ReceiptView(GenericView):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]

    def filter_queryset(self, filters, excludes):
        filters["user"] = self.request.user
        filter_q = Q(**filters)
        exclude_q = Q(**excludes)
        return self.queryset.filter(filter_q).exclude(exclude_q)


class VendorView(GenericView):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]


class ReceiptItemView(GenericView):
    queryset = ReceiptItem.objects.all()
    serializer_class = ReceiptItemSerializer
    permission_classes = [IsAuthenticated]

    def pre_create(self, request):
        request.data["receipt"] = Receipt.objects.get(id=request.data["receipt"])
