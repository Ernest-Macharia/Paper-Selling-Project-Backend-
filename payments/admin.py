from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.timezone import now

from payments.services.payout_service import disburse_withdrawal
from payments.services.refund_service import process_refund

from .models import Payment, PaymentEvent, WithdrawalRequest


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "order_id",
        "gateway",
        "amount",
        "currency",
        "status",
        "refund_button",
    )
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


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "method",
        "status",
        "created_at",
        "approved_at",
        "paid_at",
        "payout_action",
    )
    list_filter = ("status", "method", "created_at")
    search_fields = ("user__email",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "approved_at", "paid_at", "failure_reason")
    actions = ["approve_withdrawals", "mark_as_paid"]

    def approve_withdrawals(self, request, queryset):
        updated = 0
        for withdrawal in queryset.filter(status="pending"):
            withdrawal.status = "approved"
            withdrawal.approved_at = now()
            withdrawal.save()
            updated += 1
        self.message_user(request, f"✅ Approved {updated} withdrawal(s).")

    approve_withdrawals.short_description = "✅ Approve selected withdrawals"

    def mark_as_paid(self, request, queryset):
        updated = 0
        for withdrawal in queryset.filter(status="approved"):
            try:
                result = disburse_withdrawal(withdrawal)
                if result["status"] == "success":
                    withdrawal.status = "paid"
                    withdrawal.paid_at = now()
                    withdrawal.failure_reason = ""
                else:
                    withdrawal.status = "failed"
                    withdrawal.failure_reason = result.get("error", "Unknown error")
                withdrawal.save()
                updated += 1
            except Exception as e:
                withdrawal.status = "failed"
                withdrawal.failure_reason = str(e)
                withdrawal.save()
        self.message_user(request, f"💸 Processed {updated} payout(s).")

    mark_as_paid.short_description = "💸 Process & Mark selected as Paid"

    def payout_action(self, obj):
        if obj.status == "approved":
            url = reverse("admin:withdrawal-pay", args=[obj.pk])
            return format_html('<a class="button" href="{}">Pay Now</a>', url)
        return "-"

    payout_action.short_description = "Payout"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:withdrawal_id>/pay/",
                self.admin_site.admin_view(self.process_single_withdrawal),
                name="withdrawal-pay",
            ),
        ]
        return custom_urls + urls

    def process_single_withdrawal(self, request, withdrawal_id):
        withdrawal = self.get_object(request, withdrawal_id)

        if withdrawal.status != "approved":
            self.message_user(
                request, "❌ Withdrawal is not approved.", level=messages.ERROR
            )
            return redirect("..")

        try:
            result = disburse_withdrawal(withdrawal)
            if result["status"] == "success":
                self.message_user(request, f"✅ Withdrawal {withdrawal.id} paid.")
            else:
                self.message_user(
                    request, f"❌ Failed: {result.get('error')}", level=messages.ERROR
                )
        except Exception as e:
            self.message_user(
                request, f"❌ Exception occurred: {str(e)}", level=messages.ERROR
            )

        return redirect("..")
