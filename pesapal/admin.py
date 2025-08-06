import json

from django.contrib import admin
from django.utils.html import format_html

from payments.models import Payment

from .models import PesapalPayment


@admin.register(PesapalPayment)
class PesapalPaymentAdmin(admin.ModelAdmin):
    list_display = ("tracking_id", "order", "status", "payment_method", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("tracking_id", "order__id", "merchant_reference")
    readonly_fields = ("created_at", "updated_at", "raw_callback_data_prettified")
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "order",
                    "payment",
                    "tracking_id",
                    "merchant_reference",
                    "ipn_id",
                )
            },
        ),
        ("Status", {"fields": ("status", "payment_method")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
        (
            "Raw Data",
            {"fields": ("raw_callback_data_prettified",), "classes": ("collapse",)},
        ),
    )

    def raw_callback_data_prettified(self, instance):
        if instance.raw_callback_data:
            return format_html(
                "<pre>{}</pre>", json.dumps(instance.raw_callback_data, indent=2)
            )
        return "-"

    raw_callback_data_prettified.short_description = "Raw Callback Data"


# Update Payment admin if needed
class PaymentAdmin(admin.ModelAdmin):
    # ... existing configuration ...
    list_display = (
        "id",
        "gateway",
        "status",
        "amount",
        "order",
        "created_at",
    )  # Add gateway to display
    list_filter = ("gateway", "status", "created_at")  # Add gateway to filters


admin.site.unregister(Payment)  # If already registered
admin.site.register(Payment, PaymentAdmin)
