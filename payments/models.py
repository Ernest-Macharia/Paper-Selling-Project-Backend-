from django.db import models
from django.utils import timezone


class Payment(models.Model):
    GATEWAY_CHOICES = (
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("mpesa", "Mpesa"),
    )

    STATUS_CHOICES = (
        ("created", "Created"),
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    external_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    customer_email = models.EmailField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.gateway} {self.amount} {self.status}"
