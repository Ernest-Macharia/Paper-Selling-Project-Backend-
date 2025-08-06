from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.payment_views.checkout import CheckoutInitiateView, unified_checkout
from payments.payment_views.refunds import refund_payment
from payments.services.webhooks import (
    mpesa_webhook,
    paypal_webhook,
    pesapal_callback_view,
    stripe_webhook,
)
from payments.views import (
    PayoutInfoView,
    WalletSummaryView,
    WithdrawalRequestViewSet,
    stripe_oauth_callback,
    update_payout_info,
    verify_payment,
)
from payments.webhooks.paystack_webhooks import handle_paystack_webhook
from payments.webhooks.pesapal_webhooks import handle_pesapal_event

router = DefaultRouter()
router.register(r"withdrawals", WithdrawalRequestViewSet, basename="withdrawal")

urlpatterns = [
    # Main unified checkout
    path("checkout/unified/", unified_checkout, name="unified_checkout"),
    # Main frontend checkout API
    path(
        "checkout/initiate/", CheckoutInitiateView.as_view(), name="checkout_initiate"
    ),
    path("verify/", verify_payment, name="verify-payment"),
    path("payout-info/", PayoutInfoView.as_view(), name="payout-info"),
    path("payments/payout-info/update/", update_payout_info, name="update-payout-info"),
    # Refund API
    path("refund/<int:payment_id>/", refund_payment, name="refund_payment"),
    path("stripe/oauth/callback/", stripe_oauth_callback, name="stripe-oauth-callback"),
    # Webhooks
    path("webhooks/stripe/", stripe_webhook, name="stripe_webhook"),
    path("webhooks/paypal/", paypal_webhook, name="paypal_webhook"),
    path("webhooks/mpesa/", mpesa_webhook, name="mpesa_webhook"),
    path("webhooks/paystack/", handle_paystack_webhook),
    path(
        "webhooks/pesapal/<uuid:order_id>/",
        handle_pesapal_event,
        name="pesapal-webhook",
    ),
    path(
        "pesapal/callback/<uuid:order_id>/",
        pesapal_callback_view,
        name="pesapal-callback",
    ),
    path("wallet/summary/", WalletSummaryView.as_view(), name="wallet-summary"),
    path("", include(router.urls)),
]
