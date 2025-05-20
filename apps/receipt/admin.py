from django.contrib import admin
from .models import Receipt, Vendor, ReceiptItem


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "email", "contact_number", "establishment")
    search_fields = ("name", "address", "email")
    list_filter = ("establishment",)


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "user",
        "category",
        "total_expediture",
        "payment_method",
        "vendor",
        "created_at",
    )
    list_filter = ("category", "payment_method", "created_at")
    search_fields = ("title", "user__email", "vendor__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ReceiptItem)
class ReceiptItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "quantity",
        "price",
        "subtotal_expenditure",
        "receipt",
        "deductable_amount",
    )
    list_filter = ("receipt",)
    search_fields = ("title", "receipt__title")
