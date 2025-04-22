from rest_framework import serializers
from .models import Receipt, Vendor, ReceiptItem
from apps.document.serializers import DocumentSerializer
from apps.camera.serializers import ImageSerializer


class VendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendor
        fields = "__all__"


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = "__all__"


class ReceiptItemSerializer(serializers.ModelSerializer):
    receipt = ReceiptSerializer()

    class Meta:
        model = ReceiptItem
        fields = "__all__"
