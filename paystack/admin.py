# paystack_api/admin.py
from django.contrib import admin

from .models import PaystackPayment


class PaystackPaymentAdmin(admin.ModelAdmin):
    list_display = ("reference", "payment", "access_code", "created_at")
    list_filter = ("created_at",)
    search_fields = ("reference", "payment__external_id", "payment__customer_email")
    readonly_fields = ("reference", "access_code", "authorization_url", "created_at")
    raw_id_fields = ("payment",)

    fieldsets = (
        (
            "Basic Info",
            {"fields": ("payment", "reference", "access_code", "created_at")},
        ),
        (
            "Additional Data",
            {"fields": ("authorization_url", "metadata"), "classes": ("collapse",)},
        ),
    )


admin.site.register(PaystackPayment, PaystackPaymentAdmin)
