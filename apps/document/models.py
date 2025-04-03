from django.db import models
from apps.account.models import CustomUser


class Document(models.Model):
    class Type(models.TextChoices):
        RECEIPT = "RECEIPT"
        INVOICE = "INVOICE"
        OTHER = "OTHER"

    title = models.CharField(max_length=255)
    document_url = models.URLField()
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    type = models.CharField(max_length=255, choices=Type.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
