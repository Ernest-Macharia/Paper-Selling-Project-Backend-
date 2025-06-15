from django.db import models
from django.utils.timezone import now

from payments.models import Payment


class PayPalPayment(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("approved", "Approved"),
        ("captured", "Captured"),
        ("failed", "Failed"),
    ]

    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="paypal_payment"
    )
    paypal_order_id = models.CharField(max_length=100, unique=True)
    payer_id = models.CharField(max_length=100, null=True, blank=True)
    payer_email = models.EmailField(null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    capture_status = models.CharField(max_length=50, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(default=now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.paypal_order_id} — {self.status}"

    class Meta:
        verbose_name = "PayPal Payment"
        verbose_name_plural = "PayPal Payments"
