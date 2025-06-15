from django.contrib import admin

from .models import StripePayment


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "session_id",
        "payment_intent_id",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("session_id", "payment_intent_id")
    ordering = ("-created_at",)
