from rest_framework import serializers
from .models import Receipt, Vendor, ReceiptItem
from apps.document.serializers import DocumentSerializer
from apps.camera.serializers import ImageSerializer


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"


class ReceiptItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceiptItem
        fields = "__all__"


class ReceiptSerializer(serializers.ModelSerializer):
    items = ReceiptItemSerializer(many=True)

    class Meta:
        model = Receipt
        fields = "__all__"
