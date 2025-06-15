from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment_gateway",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("payment_gateway", "status", "currency")
    search_fields = ("id", "external_id")
    ordering = ("-created_at",)
