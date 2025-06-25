import json

from django.contrib import admin
from django.utils.html import escape, format_html

from paypal_api.refund import process_paypal_refund

from .models import PayPalPayment


@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "paypal_link",
        "payer_id",
        "payer_email",
        "amount",
        "status",
        "capture_status",
        "view_events_link",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("paypal_order_id", "payer_id", "payer_email")
    ordering = ("-created_at",)
    readonly_fields = (
        "paypal_order_id",
        "created_at",
        "updated_at",
        "formatted_metadata",
    )
    date_hierarchy = "created_at"
    actions = ["refund_paypal_payment"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "payment",
                    "paypal_order_id",
                    "status",
                    "amount",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Payer Info",
            {
                "fields": (
                    "payer_id",
                    "payer_email",
                    "capture_status",
                )
            },
        ),
        (
            "Debug Info",
            {
                "fields": ("formatted_metadata",),
            },
        ),
    )

    def formatted_metadata(self, obj):
        pretty_json = json.dumps(obj.metadata or {}, indent=2)
        return format_html("<pre>{}</pre>", pretty_json)

    formatted_metadata.short_description = "PayPal Metadata"

    def paypal_link(self, obj):
        if not obj.paypal_order_id:
            return "-"
        safe_order_id = escape(obj.paypal_order_id)
        safe_url = f"https://www.paypal.com/activity/payment/{safe_order_id}"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">{}</a>',
            safe_url,
            safe_order_id,
        )

    paypal_link.short_description = "PayPal Link"
    paypal_link.admin_order_field = "paypal_order_id"

    def view_events_link(self, obj):
        if not obj.payment:
            return "-"
        safe_payment_id = escape(str(obj.payment.id))
        safe_url = f"/admin/payments/paymentevent/?payment__id__exact={safe_payment_id}"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">📄 View Events</a>',
            safe_url,
        )

    view_events_link.short_description = "Events"

    def refund_paypal_payment(self, request, queryset):
        for obj in queryset:
            result = process_paypal_refund(obj)
            if result["status"] == "success":
                self.message_user(
                    request, f"✅ Refunded {obj.paypal_order_id} successfully."
                )
            else:
                self.message_user(
                    request,
                    f"❌ Refund failed for {obj.paypal_order_id}: {result.get('error')}",
                    level="error",
                )

    refund_paypal_payment.short_description = "💸 Refund selected PayPal payments"
