from django.contrib import admin

from .models import PayPalPayment


@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "paypal_order_id",
        "payer_id",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("paypal_order_id", "payer_id")
    ordering = ("-created_at",)
