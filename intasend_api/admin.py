from django.contrib import admin

from .models import IntaSendPayment


@admin.register(IntaSendPayment)
class IntaSendPaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "payment", "created_at")
    search_fields = ("invoice_id", "payment__customer_email", "payment__order__id")
    readonly_fields = ("created_at", "metadata")
