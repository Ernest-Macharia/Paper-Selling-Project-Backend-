from django.db import models

from exampapers.models import Order


class PesapalPayment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="pesapal_payments"
    )
    payment = models.OneToOneField(
        "payments.Payment", on_delete=models.CASCADE, related_name="pesapal_payment"
    )
    tracking_id = models.CharField(max_length=255, unique=True)
    merchant_reference = models.CharField(max_length=255, unique=True)
    ipn_id = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING"
    )
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    raw_callback_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pesapal Payment"
        verbose_name_plural = "Pesapal Payments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pesapal Payment {self.tracking_id} ({self.status})"
