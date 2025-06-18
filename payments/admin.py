from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from payments.services.refund_service import process_refund

from .models import Payment, PaymentEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order_id", "amount", "currency", "status", "refund_button")
    list_filter = ("gateway", "status", "currency")
    search_fields = ("id", "external_id")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    def refund_button(self, obj):
        if obj.status == "completed":
            return format_html(
                '<a class="button" href="{}">Refund</a>',
                reverse("admin:payments_refund", args=[obj.id]),
            )
        return "-"

    refund_button.short_description = "Refund"

    # Custom admin URL
    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "refund/<int:payment_id>/",
                self.admin_site.admin_view(self.process_refund),
                name="payments_refund",
            )
        ]
        return custom_urls + urls

    def process_refund(self, request, payment_id):
        result = process_refund(payment_id)
        self.message_user(request, f"Refund result: {result}")
        from django.shortcuts import redirect

        return redirect(request.META.get("HTTP_REFERER", "/admin/"))


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ["id", "payment", "gateway", "event_type", "created_at"]
    list_filter = ["gateway", "event_type"]
    search_fields = ["payment__transaction_id"]
