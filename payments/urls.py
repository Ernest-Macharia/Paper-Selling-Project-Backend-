from django.urls import include, path
from rest_framework.routers import DefaultRouter

from payments.payment_views.checkout import CheckoutInitiateView, unified_checkout
from payments.payment_views.refunds import refund_payment
from payments.services.webhooks import mpesa_webhook, paypal_webhook, stripe_webhook
from payments.views import WithdrawalRequestViewSet, verify_payment

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
    # Refund API
    path("refund/<int:payment_id>/", refund_payment, name="refund_payment"),
    # Webhooks
    path("webhooks/stripe/", stripe_webhook, name="stripe_webhook"),
    path("webhooks/paypal/", paypal_webhook, name="paypal_webhook"),
    path("webhooks/mpesa/", mpesa_webhook, name="mpesa_webhook"),
    path("", include(router.urls)),
]
