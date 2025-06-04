from django.db import models
from apps.camera.models import Image
from apps.account.models import CustomUser
from apps.document.models import Document


class ReceiptImage(models.Model):
    title = models.CharField(max_length=255)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    image_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Vendor(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    email = models.EmailField()
    contact_number = models.CharField(max_length=255)
    establishment = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Receipt(models.Model):
    class Category(models.TextChoices):
        UTILITIES = "UTILITIES"
        FOOD = "FOOD"
        TRANSPORTATION = "TRANSPORTATION"
        ENTERTAINMENT = "ENTERTAINMENT"
        OTHER = "OTHER"

    title = models.CharField(max_length=255)
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    category = models.CharField(max_length=255, choices=Category.choices)
    image = models.ForeignKey(ReceiptImage, on_delete=models.CASCADE)
    total_expenditure = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=255)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, null=True, blank=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2)
    value_added_tax = models.DecimalField(max_digits=10, decimal_places=2)
    is_deductible = models.BooleanField(default=False)
    deductible_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def items(self):
        return self.receiptitem_set.all()


class ReceiptItem(models.Model):
    title = models.CharField(max_length=255)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal_expenditure = models.DecimalField(max_digits=10, decimal_places=2)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE)
    deductable_amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
