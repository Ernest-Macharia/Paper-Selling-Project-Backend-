from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.timezone import now

from payments.services.payout_service import disburse_withdrawal
from payments.services.refund_service import process_refund

from .models import (
    OrganizationAccount,
    Payment,
    PaymentEvent,
    UserPayoutProfile,
    Wallet,
    WithdrawalRequest,
)


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

    def get_urls(self):
        return [
            path(
                "refund/<int:payment_id>/",
                self.admin_site.admin_view(self.process_refund),
                name="payments_refund",
            ),
        ] + super().get_urls()

    def process_refund(self, request, payment_id):
        result = process_refund(payment_id)
        self.message_user(request, f"Refund result: {result}")
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
        pending_qs = queryset.filter(status="pending")
        updated = pending_qs.update(status="approved", approved_at=now())
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
            try:
                url = reverse("admin:payments_withdrawalrequest_pay", args=[obj.pk])
                return format_html(
                    '<a class="button btn btn-sm btn-primary" href="{}">Pay Now</a>',
                    url,
                )
            except Exception:
                return "-"
        return "-"

    payout_action.short_description = "Payout"

    def get_urls(self):
        return [
            path(
                "<int:withdrawal_id>/pay/",
                self.admin_site.admin_view(self.process_single_withdrawal),
                name="payments_withdrawalrequest_pay",
            ),
        ] + super().get_urls()

    def process_single_withdrawal(self, request, withdrawal_id):
        withdrawal = self.get_object(request, withdrawal_id)

        if not withdrawal:
            self.message_user(request, "❌ Withdrawal not found.", level=messages.ERROR)
            return redirect("..")

        if withdrawal.status != "approved":
            self.message_user(
                request, "❌ Withdrawal is not approved.", level=messages.ERROR
            )
            return redirect("..")

        try:
            result = disburse_withdrawal(withdrawal)
            if result["status"] == "success":
                withdrawal.status = "paid"
                withdrawal.paid_at = now()
                withdrawal.failure_reason = ""
                self.message_user(request, f"✅ Withdrawal {withdrawal.id} paid.")
            else:
                withdrawal.status = "failed"
                withdrawal.failure_reason = result.get("error", "Unknown error")
                self.message_user(
                    request,
                    f"❌ Failed: {withdrawal.failure_reason}",
                    level=messages.ERROR,
                )
            withdrawal.save()
        except Exception as e:
            withdrawal.status = "failed"
            withdrawal.failure_reason = str(e)
            withdrawal.save()
            self.message_user(
                request,
                f"❌ Exception occurred: {str(e)}",
                level=messages.ERROR,
            )

        return redirect("..")


@admin.register(OrganizationAccount)
class OrgAccountAdmin(admin.ModelAdmin):
    list_display = ("available_balance", "total_earnings", "last_updated")


@admin.register(UserPayoutProfile)
class UserPayoutProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "paypal_email", "stripe_account_id", "mpesa_phone")


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "available_balance",
        "total_earned",
        "total_withdrawn",
        "last_withdrawal_at",
    )
    search_fields = ("user__email", "user__username")
