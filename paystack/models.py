from django.db import models

from payments.models import Payment


class PaystackPayment(models.Model):
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="paystack_payment"
    )
    reference = models.CharField(max_length=100, unique=True)
    access_code = models.CharField(max_length=100)
    authorization_url = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
