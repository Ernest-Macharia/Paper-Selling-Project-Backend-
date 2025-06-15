from django.db import models

from payments.models import Payment


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# M-pesa Payment models


class MpesaCalls(BaseModel):
    ip_address = models.TextField()
    caller = models.TextField()
    conversation_id = models.TextField()
    content = models.TextField()

    class Meta:
        verbose_name = "Mpesa Call"
        verbose_name_plural = "Mpesa Calls"


class MpesaCallBacks(BaseModel):
    ip_address = models.TextField()
    caller = models.TextField()
    conversation_id = models.TextField()
    content = models.TextField()

    class Meta:
        verbose_name = "Mpesa Call Back"
        verbose_name_plural = "Mpesa Call Backs"


class MpesaPayment(BaseModel):
    payment = models.OneToOneField(
        Payment, on_delete=models.CASCADE, null=True, blank=True
    )
    checkout_request_id = models.CharField(max_length=255, null=True, blank=True)
    merchant_request_id = models.CharField(max_length=100, null=True, blank=True)
    mpesa_receipt_number = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15)
    transaction_date = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
