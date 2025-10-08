from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from exampapers.models import Order


class Payment(models.Model):
    GATEWAY_CHOICES = (
        ("stripe", "Stripe"),
        ("paypal", "PayPal"),
        ("mpesa", "Mpesa"),
        ("paystack", "Paystack"),
        ("pesapal", "PesaPal"),
        ("intasend", "Intasend"),
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


class WithdrawalRequest(models.Model):
    PAYOUT_METHODS = (
        ("paypal", "PayPal"),
        ("stripe", "Stripe"),
        ("mpesa", "M-Pesa"),
        ("Paystack", "Paystack"),
        ("pesapal", "PesaPal"),
        ("intasend", "Intasend"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=20, choices=PAYOUT_METHODS)
    destination = models.CharField(max_length=255, blank=True, null=True)
    transaction_reference = models.CharField(max_length=255, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} - {self.amount} ({self.status})"


class UserPayoutProfile(models.Model):
    PAYOUT_METHODS = (
        ("paypal", "PayPal"),
        ("stripe", "Stripe"),
        ("mpesa", "M-Pesa"),
        ("Paystack", "Paystack"),
        ("pesapal", "PesaPal"),
        ("intasend", "Intasend"),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    paypal_email = models.EmailField(blank=True, null=True)
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True)
    mpesa_phone = models.CharField(max_length=20, blank=True, null=True)

    preferred_method = models.CharField(
        max_length=20, choices=PAYOUT_METHODS, blank=True, null=True
    )


class OrganizationAccount(models.Model):
    total_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Org Account | Available: {self.available_balance}"


class Wallet(models.Model):
    class Currency(models.TextChoices):
        USD = "USD", _("US Dollar")
        EUR = "EUR", _("Euro")
        KES = "KES", _("Kenyan Shilling")
        GBP = "GBP", _("British Pound")

    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    currency = models.CharField(
        max_length=3, choices=Currency.choices, default=Currency.USD
    )
    available_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_withdrawal_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
