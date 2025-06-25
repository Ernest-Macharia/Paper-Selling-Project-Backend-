import json

from django.contrib import admin
from django.utils.html import escape, format_html

from stripe_api.refund import process_stripe_refund

from .models import StripePayment


@admin.register(StripePayment)
class StripePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "payment",
        "session_id",
        "payment_intent",
        "view_events_link",
        "created_at",
    )
    search_fields = ("session_id", "payment_intent")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "formatted_metadata")
    date_hierarchy = "created_at"
    actions = ["refund_stripe_payment"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "payment",
                    "session_id",
                    "payment_intent",
                    "created_at",
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

    formatted_metadata.short_description = "Stripe Metadata"

    def view_events_link(self, obj):
        if not obj.payment:
            return "-"
        safe_payment_id = escape(str(obj.payment.id))
        url = f"/admin/payments/paymentevent/?payment__id__exact={safe_payment_id}\
            &gateway__exact=stripe"
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">📄 View Events</a>',
            url,
        )

    view_events_link.short_description = "Events"

    def refund_stripe_payment(self, request, queryset):
        for obj in queryset:
            result = process_stripe_refund(obj)
            if result["status"] == "success":
                self.message_user(
                    request, f"✅ Refunded {obj.payment_intent} successfully."
                )
            else:
                self.message_user(
                    request,
                    f"❌ Refund failed for {obj.payment_intent}: {result.get('error')}",
                    level="error",
                )

    refund_stripe_payment.short_description = "💸 Refund selected Stripe payments"
