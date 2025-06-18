from django.contrib import admin

from .models import MpesaPayment


@admin.register(MpesaPayment)
class MpesaPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "phone_number",
        "checkout_request_id",
        "merchant_request_id",
        "mpesa_receipt_number",
        "transaction_date",
    )
    search_fields = ("phone_number", "mpesa_receipt_number", "checkout_request_id")
    ordering = ("-transaction_date",)
