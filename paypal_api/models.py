from django.db import models
from django.utils.timezone import now


class PayPalPayment(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("approved", "Approved"),
        ("captured", "Captured"),
        ("failed", "Failed"),
    ]

    paypal_order_id = models.CharField(max_length=64, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.paypal_order_id} — {self.status}"

    class Meta:
        verbose_name = "PayPal Payment"
        verbose_name_plural = "PayPal Payments"
