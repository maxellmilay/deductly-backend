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
    vendor = VendorSerializer()
    items = ReceiptItemSerializer(many=True)

    class Meta:
        model = Receipt
        fields = "__all__"

    def create(self, validated_data):
        vendor_data = validated_data.pop("vendor")
        items_data = validated_data.pop("items")

        # Create or get vendor
        vendor, _ = Vendor.objects.get_or_create(
            name=vendor_data["name"], defaults=vendor_data
        )

        # Create receipt
        receipt = Receipt.objects.create(vendor=vendor, **validated_data)

        # Create receipt items
        for item_data in items_data:
            ReceiptItem.objects.create(receipt=receipt, **item_data)

        return receipt
