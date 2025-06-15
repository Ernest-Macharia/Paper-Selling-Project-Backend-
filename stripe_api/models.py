from django.db import models

from payments.models import Payment


class StripePayment(models.Model):
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, related_name="stripe_payment"
    )
    session_id = models.CharField(max_length=100, unique=True)
    payment_intent = models.CharField(max_length=100)
    customer_id = models.CharField(max_length=100, null=True, blank=True)
    charge_id = models.CharField(max_length=100, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
