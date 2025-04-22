from django.contrib import admin
from .models import Receipt, Vendor, ReceiptItem

# Register your models here.

admin.site.register(Receipt)
admin.site.register(Vendor)
admin.site.register(ReceiptItem)
