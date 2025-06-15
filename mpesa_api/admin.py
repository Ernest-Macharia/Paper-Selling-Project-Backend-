from django.contrib import admin

from .models import MpesaPayment


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "phone_number",
        "amount",
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt_number",
        "status",
        "transaction_date",
    )
    list_filter = ("status",)
    search_fields = ("phone_number", "mpesa_receipt_number", "checkout_request_id")
    ordering = ("-transaction_date",)
