# payments/views.py
# Optionally log config for debugging
import logging

import paypalrestsdk  # ← main SDK
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import PayPalPayment

logger = logging.getLogger(__name__)
logger.info("PayPal SDK configured in %s mode", settings.PAYPAL_MODE)

# ──────────────────────────────────────────────────────────
# 1)  Configure PayPal SDK once when this module is imported
# ──────────────────────────────────────────────────────────
paypalrestsdk.configure(
    {
        "mode": settings.PAYPAL_MODE,  # 'sandbox'  or 'live'
        "client_id": settings.PAYPAL_CLIENT_ID,
        "client_secret": settings.PAYPAL_CLIENT_SECRET,
    }
)


# ──────────────────────────────────────────────────────────
# 2)  Create PayPal payment (returns orderID & approval URL)
# ──────────────────────────────────────────────────────────
@api_view(["POST"])
@permission_classes([AllowAny])
def paypal_create(request):
    """
    POST  { "amount": 12.34 }
    RSP   { "orderID": "...", "approve_url": "https://www.sandbox.paypal.com/..." }
    """
    amount = request.data.get("amount")
    if amount is None:
        return Response(
            {"detail": "amount required"}, status=status.HTTP_400_BAD_REQUEST
        )

    payment = paypalrestsdk.Payment(
        {
            "intent": "sale",  # classic immediate capture flow
            "payer": {"payment_method": "paypal"},
            "transactions": [
                {
                    "amount": {"total": f"{float(amount):.2f}", "currency": "USD"},
                    "description": "Paper purchase",
                }
            ],
            "redirect_urls": {
                "return_url": settings.PAYPAL_RETURN_URL,
                "cancel_url": settings.PAYPAL_CANCEL_URL,
            },
        }
    )

    if not payment.create():
        logger.error("PayPal create error: %s", payment.error)
        return Response(payment.error, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # store minimal record
    PayPalPayment.objects.create(
        paypal_order_id=payment.id, amount=float(amount), status="created"
    )

    approval_url = next(
        (approve.href for approve in payment.links if approve.rel == "approval_url"),
        None,
    )
    return Response({"orderID": payment.id, "approve_url": approval_url})


# ──────────────────────────────────────────────────────────
# 3)  Capture / Execute PayPal payment after buyer approval
# ──────────────────────────────────────────────────────────
@api_view(["POST"])
@permission_classes([AllowAny])
def paypal_capture(request):
    """
    POST  { "orderID": "...", "payerID": "..." }
    RSP   PayPal capture details
    """
    order_id = request.data.get("orderID")
    payer_id = request.data.get("payerID")  # returned by PayPal to your front-end

    if not order_id or not payer_id:
        return Response(
            {"detail": "orderID and payerID required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payment = paypalrestsdk.Payment.find(order_id)
    except paypalrestsdk.ResourceNotFound as e:
        logger.error("Payment not found: %s", e)
        return Response(
            {"detail": "payment not found"}, status=status.HTTP_404_NOT_FOUND
        )
    if not payment:
        return Response(
            {"detail": "payment not found"}, status=status.HTTP_404_NOT_FOUND
        )

    if not payment.execute({"payer_id": payer_id}):
        logger.error("PayPal execute error: %s", payment.error)
        return Response(payment.error, status=status.HTTP_400_BAD_REQUEST)

    # update DB
    PayPalPayment.objects.filter(paypal_order_id=order_id).update(status="captured")

    return Response(payment.to_dict())


def paypal_payment_success(request):
    return HttpResponse(
        "<h1>✅ Payment was successful!</h1><p>Thank you for your purchase.</p>"
    )


def paypal_payment_cancelled(request):
    return HttpResponse(
        "<h1>❌ Payment was cancelled.</h1><p>You can try again at any time.</p>"
    )
