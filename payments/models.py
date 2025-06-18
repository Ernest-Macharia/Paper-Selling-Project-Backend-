from django.db import models
from django.utils import timezone

from exampapers.models import Order


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

    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name="payment", null=True, blank=True
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
        return f"{self.gateway.upper()} Payment {self.external_id}"


class PaymentEvent(models.Model):
    EVENT_TYPES = (
        ("payment_succeeded", "Payment Succeeded"),
        ("payment_failed", "Payment Failed"),
        ("refund_requested", "Refund Requested"),
        ("refund_succeeded", "Refund Succeeded"),
        ("refund_failed", "Refund Failed"),
        ("webhook_received", "Webhook Received"),
    )

    payment = models.ForeignKey(Payment, on_delete=models.CASCADE)
    gateway = models.CharField(max_length=50)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    payload = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gateway} | {self.event_type} | {self.payment.id}"
