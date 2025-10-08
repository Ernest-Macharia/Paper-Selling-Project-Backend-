from django.db import models

from payments.models import Payment


class IntaSendPayment(models.Model):
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="intasend_payment"
    )
    invoice_id = models.CharField(max_length=100, unique=True)
    checkout_url = models.URLField(max_length=500)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"IntaSend Payment {self.invoice_id}"
