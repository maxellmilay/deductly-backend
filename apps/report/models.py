from django.db import models
from apps.account.models import CustomUser


class Report(models.Model):
    class Category(models.TextChoices):
        DAILY = "DAILY"
        WEEKLY = "WEEKLY"
        MONTHLY = "MONTHLY"
        YEARLY = "YEARLY"

    title = models.CharField(max_length=255)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.CharField(max_length=255, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    grand_total_expenditure = models.DecimalField(max_digits=10, decimal_places=2)
    total_tax_deductions = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
